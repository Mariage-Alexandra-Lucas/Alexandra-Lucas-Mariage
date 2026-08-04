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

gateway.PORT = 8788
gateway.VERSION = "2.0.0"
WEB_ORIGIN = "https://alpesex.github.io"

cfg = gateway.load_config()
cfg["allowed_origin"] = WEB_ORIGIN
cfg["nas_root"] = cfg.get("nas_root") or r"X:\Mariage_Alexandra_Lucas"
gateway.save_config(cfg)


def safe(value: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in value).strip("._") or "fichier"


def root(config: dict) -> Path:
    return Path(config["nas_root"])


def ensure_tree(config: dict) -> None:
    base = root(config)
    for rel in ["Configuration", "Photos/Privees", "Photos/Stories", "Jeu/Questions", "Jeu/Reponses", "Jeu/Scores", "Jeu/Historique", "Sauvegardes", "Logs", "Temp"]:
        (base / rel).mkdir(parents=True, exist_ok=True)


def read_meta(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_private(config: dict, user: dict, all_users: bool) -> list[dict]:
    base = root(config) / "Photos" / "Privees"
    folders = [p for p in base.iterdir() if p.is_dir()] if all_users and base.exists() else [base / safe(user["name"])]
    items = []
    for folder in folders:
        if not folder.exists():
            continue
        for meta_file in folder.glob("*.json"):
            meta = read_meta(meta_file)
            if meta:
                items.append(meta)
    return sorted(items, key=lambda x: x.get("createdAt", ""), reverse=True)


def list_stories(config: dict) -> list[dict]:
    folder = root(config) / "Photos" / "Stories"
    if not folder.exists():
        return []
    items = [m for p in folder.glob("*.json") if (m := read_meta(p))]
    return sorted(items, key=lambda x: x.get("createdAt", ""), reverse=True)


class V2Handler(gateway.GatewayHandler):
    server_version = "MariageGateway/2.0"

    def _user_any(self):
        token = self.headers.get("Authorization", "").replace("Bearer ", "", 1)
        if not token:
            token = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return gateway.verify_token(token, self.server.config["token_secret"])

    def do_GET(self):
        route = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        if route == "/api/photos":
            user = self._user_any()
            if not user:
                self._json({"error": "Session invalide."}, 401); return
            scope = query.get("scope", ["mine"])[0]
            self._json(list_private(self.server.config, user, user["role"] == "superadmin" and scope == "all")); return
        if route == "/api/stories":
            if not self._user_any():
                self._json({"error": "Session invalide."}, 401); return
            self._json(list_stories(self.server.config)); return
        if route == "/api/media":
            user = self._user_any()
            if not user:
                self._json({"error": "Session invalide."}, 401); return
            kind = query.get("kind", [""])[0]
            owner = safe(query.get("owner", [""])[0])
            filename = safe(query.get("file", [""])[0])
            if kind == "story":
                path = root(self.server.config) / "Photos" / "Stories" / filename
            elif kind == "photo":
                if user["role"] != "superadmin" and safe(user["name"]) != owner:
                    self._json({"error": "Accès refusé."}, 403); return
                path = root(self.server.config) / "Photos" / "Privees" / owner / filename
            else:
                self._json({"error": "Média invalide."}, 400); return
            if not path.exists() or not path.is_file():
                self._json({"error": "Média introuvable."}, 404); return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", WEB_ORIGIN)
            self.end_headers(); self.wfile.write(data); return
        super().do_GET()

    def do_POST(self):
        route = urlparse(self.path).path
        if route not in ("/api/photos", "/api/stories"):
            super().do_POST(); return
        user = self._user_any()
        if not user:
            self._json({"error": "Session invalide."}, 401); return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._json({"error": "Format d’envoi invalide."}, 400); return
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type})
        field = form["photo"] if "photo" in form else None
        if field is None or not getattr(field, "file", None):
            self._json({"error": "Aucune photo reçue."}, 400); return
        original = Path(field.filename or "photo.jpg")
        ext = original.suffix.lower() if original.suffix else ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}:
            self._json({"error": "Format de photo non autorisé."}, 400); return
        ensure_tree(self.server.config)
        item_id = uuid.uuid4().hex
        filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{item_id}{ext}"
        owner = safe(user["name"])
        story = route == "/api/stories"
        folder = root(self.server.config) / "Photos" / ("Stories" if story else f"Privees/{owner}")
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / filename
        with target.open("wb") as output:
            shutil.copyfileobj(field.file, output)
        comment = str(form.getfirst("comment", ""))[:180] if story else ""
        meta = {"id": item_id, "owner": user["name"], "filename": filename, "createdAt": datetime.now().astimezone().isoformat(), "comment": comment, "kind": "story" if story else "photo", "url": f"/api/media?kind={'story' if story else 'photo'}&owner={quote(owner)}&file={quote(filename)}"}
        (folder / f"{filename}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        gateway.log(f"{user['name']} a publié {'une story' if story else 'une photo'} : {filename}")
        self._json(meta, 201)


def start_v2(self):
    self.save()
    self.config["allowed_origin"] = WEB_ORIGIN
    self.config["nas_root"] = self.config.get("nas_root") or r"X:\Mariage_Alexandra_Lucas"
    gateway.save_config(self.config)
    if not self.config["admin_password"] or not self.config["dj_password"]:
        messagebox.showwarning(gateway.APP_NAME, "Renseignez les deux mots de passe avant de démarrer."); return
    if self.server:
        return
    try:
        ensure_tree(self.config)
        self.server = gateway.GatewayServer(("127.0.0.1", gateway.PORT), V2Handler, self.config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.status.config(text="● Passerelle V2 active — port 8788", fg="#74d3ae")
        gateway.log("Passerelle mariage V2 démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None
        messagebox.showerror(gateway.APP_NAME, f"Démarrage impossible :\n{exc}")


gateway.GatewayUI.start = start_v2

if __name__ == "__main__":
    gateway.GatewayUI().run()
