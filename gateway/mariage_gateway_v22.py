from __future__ import annotations

import cgi
import json
import mimetypes
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from urllib.parse import parse_qs, quote, urlparse

import mariage_gateway as gateway
import mariage_gateway_v2 as v2

gateway.PORT = 8788
gateway.VERSION = "2.2.0"
WEB_ORIGIN = "https://alpesex.github.io"


def archive_item(config: dict, kind: str, item_id: str, user: dict) -> bool:
    base = v2.root(config) / "Photos"
    active = base / ("Stories" if kind == "story" else "Privees")
    candidates = list(active.rglob("*.json")) if active.exists() else []
    meta_file = None
    meta = None
    for candidate in candidates:
        current = v2.read_meta(candidate)
        if current and current.get("id") == item_id:
            meta_file, meta = candidate, current
            break
    if not meta_file or not meta:
        return False
    owner = str(meta.get("owner", ""))
    if user.get("role") != "superadmin" and owner != user.get("name"):
        raise PermissionError("Suppression non autorisée.")
    archive_root = base / ("Stories_Archivees" if kind == "story" else "Photos_Archivees")
    archive = archive_root / datetime.now().strftime("%Y-%m-%d") / v2.safe(owner)
    archive.mkdir(parents=True, exist_ok=True)
    media = meta_file.parent / str(meta.get("filename", ""))
    stamp = datetime.now().strftime("%H%M%S")
    if media.exists():
        shutil.move(str(media), str(archive / f"{stamp}-{media.name}"))
    meta["deletedAt"] = datetime.now().astimezone().isoformat()
    meta["deletedBy"] = user.get("name")
    (archive / f"{stamp}-{meta_file.name}").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    meta_file.unlink(missing_ok=True)
    gateway.log(f"{kind} {item_id} archivé par {user.get('name')}")
    return True


class V22Handler(v2.V2Handler):
    server_version = "MariageGateway/2.2"

    def _headers(self, status=200, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", WEB_ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def do_POST(self):
        route = urlparse(self.path).path
        if route != "/api/stories":
            super().do_POST()
            return
        user = self._user_any()
        if not user:
            self._json({"error": "Session invalide."}, 401)
            return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._json({"error": "Format d’envoi invalide."}, 400)
            return
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
        )
        field = form["photo"] if "photo" in form else None
        if field is None or not getattr(field, "file", None):
            self._json({"error": "Aucun média reçu."}, 400)
            return
        original = Path(field.filename or "story.jpg")
        ext = original.suffix.lower() or ".jpg"
        allowed = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".mp4", ".mov", ".webm"}
        if ext not in allowed:
            self._json({"error": "Format de story non autorisé."}, 400)
            return
        v2.ensure_tree(self.server.config)
        item_id = uuid.uuid4().hex
        filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{item_id}{ext}"
        folder = v2.root(self.server.config) / "Photos" / "Stories"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / filename
        with target.open("wb") as output:
            shutil.copyfileobj(field.file, output)
        media_type = "video" if ext in {".mp4", ".mov", ".webm"} else "image"
        comment = str(form.getfirst("comment", ""))[:180]
        meta = {
            "id": item_id,
            "owner": user["name"],
            "filename": filename,
            "createdAt": datetime.now().astimezone().isoformat(),
            "comment": comment,
            "kind": "story",
            "mediaType": media_type,
            "url": f"/api/media?kind=story&owner={quote(v2.safe(user['name']))}&file={quote(filename)}",
        }
        (folder / f"{filename}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        gateway.log(f"{user['name']} a publié une story {media_type}: {filename}")
        self._json(meta, 201)

    def do_DELETE(self):
        route = urlparse(self.path).path
        if route not in {"/api/stories", "/api/photos"}:
            self._json({"error": "Route inconnue."}, 404)
            return
        user = self._user_any()
        if not user:
            self._json({"error": "Session invalide."}, 401)
            return
        item_id = parse_qs(urlparse(self.path).query).get("id", [""])[0]
        if not item_id:
            self._json({"error": "Élément non précisé."}, 400)
            return
        kind = "story" if route.endswith("stories") else "photo"
        try:
            archived = archive_item(self.server.config, kind, item_id, user)
        except PermissionError as exc:
            self._json({"error": str(exc)}, 403)
            return
        if not archived:
            self._json({"error": "Élément introuvable."}, 404)
            return
        self._json({"ok": True, "archived": True})


def start_v22(self):
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
        for rel in ["Photos/Stories_Archivees", "Photos/Photos_Archivees"]:
            (v2.root(self.config) / rel).mkdir(parents=True, exist_ok=True)
        self.server = gateway.GatewayServer(("127.0.0.1", gateway.PORT), V22Handler, self.config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.status.config(text="● Passerelle V2.2 active — port 8788", fg="#74d3ae")
        gateway.log("Passerelle mariage V2.2 démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None
        messagebox.showerror(gateway.APP_NAME, f"Démarrage impossible :\n{exc}")


gateway.GatewayUI.start = start_v22

if __name__ == "__main__":
    gateway.GatewayUI().run()
