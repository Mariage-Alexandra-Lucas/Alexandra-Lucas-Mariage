from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from urllib.parse import parse_qs, urlparse

import mariage_gateway as gateway
import mariage_gateway_v2 as v2

gateway.PORT = 8788
gateway.VERSION = "2.1.0"
WEB_ORIGIN = "https://alpesex.github.io"


class V21Handler(v2.V2Handler):
    server_version = "MariageGateway/2.1"

    def _headers(self, status=200, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", WEB_ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def do_DELETE(self):
        route = urlparse(self.path).path
        if route != "/api/stories":
            self._json({"error": "Route inconnue."}, 404)
            return
        user = self._user_any()
        if not user:
            self._json({"error": "Session invalide."}, 401)
            return
        story_id = parse_qs(urlparse(self.path).query).get("id", [""])[0]
        if not story_id:
            self._json({"error": "Story non précisée."}, 400)
            return
        stories = v2.root(self.server.config) / "Photos" / "Stories"
        meta_file = next((p for p in stories.glob("*.json") if (m := v2.read_meta(p)) and m.get("id") == story_id), None)
        if not meta_file:
            self._json({"error": "Story introuvable."}, 404)
            return
        meta = v2.read_meta(meta_file) or {}
        if user.get("role") != "superadmin" and meta.get("owner") != user.get("name"):
            self._json({"error": "Vous ne pouvez supprimer que vos stories."}, 403)
            return
        archive = stories / "Supprimees" / datetime.now().strftime("%Y-%m-%d")
        archive.mkdir(parents=True, exist_ok=True)
        media = stories / str(meta.get("filename", ""))
        stamp = datetime.now().strftime("%H%M%S")
        if media.exists():
            shutil.move(str(media), str(archive / f"{stamp}-{media.name}"))
        meta["deletedAt"] = datetime.now().astimezone().isoformat()
        meta["deletedBy"] = user.get("name")
        archived_meta = archive / f"{stamp}-{meta_file.name}"
        archived_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        meta_file.unlink(missing_ok=True)
        gateway.log(f"Story {story_id} supprimée de l'application et archivée par {user.get('name')}")
        self._json({"ok": True, "archived": True})


def start_v21(self):
    self.save()
    self.config["allowed_origin"] = WEB_ORIGIN
    self.config["nas_root"] = self.config.get("nas_root") or r"X:\Mariage_Alexandra_Lucas"
    gateway.save_config(self.config)
    if not self.config["admin_password"] or not self.config["dj_password"]:
        messagebox.showwarning(gateway.APP_NAME, "Renseignez les deux mots de passe avant de démarrer.")
        return
    if self.server:
        return
    try:
        v2.ensure_tree(self.config)
        self.server = gateway.GatewayServer(("127.0.0.1", gateway.PORT), V21Handler, self.config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.status.config(text="● Passerelle V2.1 active — port 8788", fg="#74d3ae")
        gateway.log("Passerelle mariage V2.1 démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None
        messagebox.showerror(gateway.APP_NAME, f"Démarrage impossible :\n{exc}")


gateway.GatewayUI.start = start_v21

if __name__ == "__main__":
    gateway.GatewayUI().run()
