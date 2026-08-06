from __future__ import annotations

import cgi
import json
import mimetypes
import shutil
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from urllib.parse import parse_qs, quote, urlparse

import mariage_gateway as gateway
import mariage_gateway_v2 as v2
import mariage_gateway_v22 as v22

gateway.PORT = 8788
gateway.VERSION = "2.4.0"
WEB_ORIGIN = "https://mariage-alexandra-lucas.github.io"

GAME_CODES = {
    "guadeloupe": "GUA-ALEX-LUCAS-2026",
    "ile-maurice": "MAU-ALEX-LUCAS-2026",
    "maldives": "MAL-ALEX-LUCAS-2026",
    "mexique": "MEX-ALEX-LUCAS-2026",
}
TEAM_MISSIONS = [
    "Trouvez un point commun surprenant entre vous quatre.",
    "Reproduisez ensemble une pochette d’album.",
    "Formez les lettres A et L avec vos corps.",
    "Inventez un nom et une devise pour votre équipe.",
    "Représentez un film connu sur une photo.",
]
STORE_LOCK = threading.RLock()


def v24_root(config: dict) -> Path:
    return v2.root(config) / "Animations_V24"


def ensure_v24_tree(config: dict) -> None:
    v2.ensure_tree(config)
    base = v24_root(config)
    for rel in ["Medias/Livre_Or", "Medias/Binomes", "Medias/Equipes", "Medias/Defis", "Configuration", "Progression"]:
        (base / rel).mkdir(parents=True, exist_ok=True)


def store_path(config: dict, name: str) -> Path:
    ensure_v24_tree(config)
    return v24_root(config) / "Configuration" / f"{name}.json"


def read_store(config: dict, name: str, default):
    path = store_path(config, name)
    with STORE_LOCK:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default


def write_store(config: dict, name: str, value) -> None:
    path = store_path(config, name)
    with STORE_LOCK:
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)


def now() -> str:
    return datetime.now().astimezone().isoformat()


def user_key(user: dict) -> str:
    return v2.safe(str(user.get("name", "invite")))


def public_user(user: dict) -> dict:
    return {"name": user.get("name"), "table": user.get("table"), "role": user.get("role")}


def save_upload(config: dict, folder: str, field, prefix: str) -> tuple[str, Path]:
    original = Path(field.filename or "media.jpg")
    ext = original.suffix.lower() or ".jpg"
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".mp4", ".mov", ".webm", ".mp3", ".m4a", ".wav", ".ogg"}
    if ext not in allowed:
        raise ValueError("Format de média non autorisé.")
    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{prefix}-{uuid.uuid4().hex}{ext}"
    target = v24_root(config) / "Medias" / folder / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as output:
        shutil.copyfileobj(field.file, output)
    return filename, target


def media_url(folder: str, filename: str) -> str:
    return f"/api/v24/media?folder={quote(folder)}&file={quote(filename)}"


def generate_pairs(config: dict) -> list[dict]:
    families = read_store(config, "families", {})
    left = sorted([u["name"] for u in gateway.USERS if families.get(u["name"]) == "alexandra"])
    right = sorted([u["name"] for u in gateway.USERS if families.get(u["name"]) == "lucas"])
    pairs = []
    for index, (a, b) in enumerate(zip(left, right), 1):
        pairs.append({"id": f"binome-{index}", "members": [a, b], "validated": False, "photo": None})
    write_store(config, "pairs", pairs)
    return pairs


def dashboard(config: dict) -> dict:
    progress = read_store(config, "progress", {})
    guestbook = read_store(config, "guestbook", [])
    announcements = read_store(config, "announcements", [])
    pairs = read_store(config, "pairs", [])
    connected = len(progress)
    unlocked = sum(len(v.get("unlocked", [])) for v in progress.values())
    completed = sum(len(v.get("completed", [])) for v in progress.values())
    size = 0
    base = v2.root(config)
    if base.exists():
        try:
            size = sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
        except OSError:
            pass
    return {"connectedGuests": connected, "unlockedGames": unlocked, "completedGames": completed,
            "guestbookMessages": len(guestbook), "announcements": len(announcements),
            "validatedPairs": sum(1 for p in pairs if p.get("validated")), "storageBytes": size,
            "nasConnected": base.exists()}


class V24Handler(v22.V22Handler):
    server_version = "MariageGateway/2.4"

    def _user_required(self):
        user = self._user_any()
        if not user:
            self._json({"error": "Session invalide."}, 401)
        return user

    def _admin_required(self):
        user = self._user_required()
        if user and user.get("role") != "superadmin":
            self._json({"error": "Accès administrateur requis."}, 403)
            return None
        return user

    def _multipart(self):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("Format d’envoi invalide.")
        return cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type})

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)
        if not route.startswith("/api/v24/"):
            super().do_GET(); return
        user = self._user_required()
        if not user:
            return
        config = self.server.config
        ensure_v24_tree(config)
        if route == "/api/v24/state":
            progress_all = read_store(config, "progress", {})
            progress = progress_all.get(user_key(user), {"unlocked": [], "completed": [], "challengePoints": 0})
            pairs = read_store(config, "pairs", [])
            pair = next((p for p in pairs if user.get("name") in p.get("members", [])), None)
            response = {
                "announcements": read_store(config, "announcements", [])[-10:][::-1],
                "guestbook": read_store(config, "guestbook", [])[-100:][::-1],
                "program": read_store(config, "program", {"current": 0, "updatedAt": None}),
                "progress": progress,
                "pair": pair,
                "families": read_store(config, "families", {}) if user.get("role") == "superadmin" else None,
                "pairs": pairs if user.get("role") == "superadmin" else None,
                "dashboard": dashboard(config) if user.get("role") == "superadmin" else None,
                "serverTime": now(),
            }
            self._json(response); return
        if route == "/api/v24/media":
            folder = v2.safe(query.get("folder", [""])[0])
            filename = v2.safe(query.get("file", [""])[0])
            path = v24_root(config) / "Medias" / folder / filename
            if not path.exists() or not path.is_file():
                self._json({"error": "Média introuvable."}, 404); return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", WEB_ORIGIN)
            self.end_headers(); self.wfile.write(data); return
        if route == "/api/v24/souvenirs.zip":
            archive = v24_root(config) / "Album-Souvenirs-Alexandra-Lucas.zip"
            media_root = v24_root(config) / "Medias"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
                for item in media_root.rglob("*"):
                    if item.is_file():
                        output.write(item, item.relative_to(media_root))
                output.writestr("livre-or.json", json.dumps(read_store(config, "guestbook", []), ensure_ascii=False, indent=2))
            data = archive.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", 'attachment; filename="Album-Souvenirs-Alexandra-Lucas.zip"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", WEB_ORIGIN)
            self.end_headers(); self.wfile.write(data); return
        self._json({"error": "Route inconnue."}, 404)

    def do_POST(self):
        route = urlparse(self.path).path
        if not route.startswith("/api/v24/"):
            super().do_POST(); return
        user = self._user_required()
        if not user:
            return
        config = self.server.config
        ensure_v24_tree(config)
        try:
            if route == "/api/v24/unlock":
                data = self._body(); game = str(data.get("game", "")); code = str(data.get("code", ""))
                if GAME_CODES.get(game) != code:
                    self._json({"error": "QR code invalide."}, 400); return
                all_progress = read_store(config, "progress", {}); key = user_key(user)
                item = all_progress.setdefault(key, {"name": user["name"], "unlocked": [], "completed": [], "challengePoints": 0})
                if game not in item["unlocked"]: item["unlocked"].append(game)
                item["lastUpdate"] = now(); write_store(config, "progress", all_progress)
                self._json({"ok": True, "progress": item}); return
            if route == "/api/v24/game-progress":
                data = self._body(); game = str(data.get("game", "")); answers = data.get("answers")
                if game not in GAME_CODES:
                    self._json({"error": "Jeu inconnu."}, 400); return
                all_progress = read_store(config, "progress", {}); key = user_key(user)
                item = all_progress.setdefault(key, {"name": user["name"], "unlocked": [], "completed": [], "challengePoints": 0})
                if user.get("role") == "superadmin" and game not in item.get("unlocked", []):
                    item.setdefault("unlocked", []).append(game)
                if game not in item.get("unlocked", []):
                    self._json({"error": "Jeu non déverrouillé."}, 403); return
                expected_counts = {"guadeloupe": 4, "ile-maurice": 4, "mexique": 6}
                if game in expected_counts:
                    if not isinstance(answers, list) or len(answers) != expected_counts[game] or any(not str(x).strip() for x in answers):
                        self._json({"error": "Une réponse écrite est obligatoire pour chaque mission."}, 400); return
                    cleaned_answers = [str(x).strip()[:300] for x in answers]
                else:
                    if not isinstance(answers, dict):
                        self._json({"error": "Complétez les quatre épreuves du puzzle."}, 400); return
                    order = answers.get("order", []); years = answers.get("years", {})
                    place = str(answers.get("place", "")).strip().lower(); anecdote = str(answers.get("anecdote", ""))
                    correct = order == ["1", "2", "3"] and years == {"photo2021": "2021", "photo2024": "2024", "photo2015": "2015"} and place in {"mexique", "le mexique"} and anecdote == "corail"
                    if not correct:
                        self._json({"error": "Une ou plusieurs réponses du puzzle sont incorrectes. Essayez encore !"}, 400); return
                    cleaned_answers = {"order": order, "years": years, "place": "Mexique", "anecdote": anecdote}
                item.setdefault("gameAnswers", {})[game] = cleaned_answers
                if game not in item["completed"]: item["completed"].append(game)
                item["lastUpdate"] = now(); write_store(config, "progress", all_progress)
                self._json({"ok": True, "progress": item}); return
            if route == "/api/v24/announcement":
                if not self._admin_required(): return
                data = self._body(); text = str(data.get("text", "")).strip()[:280]
                if not text: self._json({"error": "Annonce vide."}, 400); return
                items = read_store(config, "announcements", [])
                items.append({"id": uuid.uuid4().hex, "text": text, "createdAt": now(), "author": user["name"]})
                write_store(config, "announcements", items); self._json(items[-1], 201); return
            if route == "/api/v24/program":
                if not self._admin_required(): return
                data = self._body(); current = max(0, min(3, int(data.get("current", 0))))
                value = {"current": current, "updatedAt": now(), "author": user["name"]}
                write_store(config, "program", value); self._json(value); return
            if route == "/api/v24/family":
                if not self._admin_required(): return
                data = self._body(); name = str(data.get("name", "")); family = str(data.get("family", ""))
                if family not in {"alexandra", "lucas", "autre", ""}: self._json({"error": "Famille invalide."}, 400); return
                families = read_store(config, "families", {}); families[name] = family
                write_store(config, "families", families); self._json({"ok": True}); return
            if route == "/api/v24/generate-pairs":
                if not self._admin_required(): return
                self._json({"pairs": generate_pairs(config)}); return
            if route in {"/api/v24/guestbook", "/api/v24/pair-proof", "/api/v24/team-proof", "/api/v24/challenge-proof"}:
                form = self._multipart(); field = form["media"] if "media" in form else None
                text = str(form.getfirst("text", ""))[:500]
                participants = [x for x in str(form.getfirst("participants", "")).split("|") if x]
                folder = {"/api/v24/guestbook": "Livre_Or", "/api/v24/pair-proof": "Binomes",
                          "/api/v24/team-proof": "Equipes", "/api/v24/challenge-proof": "Defis"}[route]
                filename = None
                if field is not None and getattr(field, "file", None):
                    filename, _ = save_upload(config, folder, field, user_key(user))
                if route == "/api/v24/guestbook":
                    if not text and not filename: self._json({"error": "Ajoutez un message ou un média."}, 400); return
                    items = read_store(config, "guestbook", [])
                    item = {"id": uuid.uuid4().hex, "author": user["name"], "text": text, "createdAt": now(),
                            "media": media_url(folder, filename) if filename else None,
                            "mediaType": mimetypes.guess_type(filename)[0] if filename else None}
                    items.append(item); write_store(config, "guestbook", items); self._json(item, 201); return
                if not filename: self._json({"error": "Une photo est obligatoire."}, 400); return
                if route == "/api/v24/pair-proof":
                    pairs = read_store(config, "pairs", [])
                    pair = next((p for p in pairs if user["name"] in p.get("members", [])), None)
                    if not pair: self._json({"error": "Aucun binôme attribué."}, 400); return
                    pair.update({"validated": True, "photo": media_url(folder, filename), "validatedAt": now(), "publishedBy": user["name"]})
                    write_store(config, "pairs", pairs); self._json(pair); return
                items = read_store(config, "proofs", [])
                item = {"id": uuid.uuid4().hex, "kind": "team" if route.endswith("team-proof") else "challenge",
                        "author": user["name"], "participants": participants, "text": text, "photo": media_url(folder, filename), "createdAt": now()}
                items.append(item); write_store(config, "proofs", items)
                all_progress = read_store(config, "progress", {})
                for person in set(participants + [user["name"]]):
                    key = v2.safe(person); p = all_progress.setdefault(key, {"name": person, "unlocked": [], "completed": [], "challengePoints": 0})
                    p["challengePoints"] = int(p.get("challengePoints", 0)) + 1
                write_store(config, "progress", all_progress); self._json(item, 201); return
        except ValueError as exc:
            self._json({"error": str(exc)}, 400); return
        except Exception as exc:
            gateway.log(f"Erreur V2.4 : {exc}")
            self._json({"error": "Impossible d’enregistrer la demande."}, 500); return
        self._json({"error": "Route inconnue."}, 404)


def start_v24(self):
    self.save()
    self.config["allowed_origin"] = WEB_ORIGIN
    self.config["nas_root"] = self.config.get("nas_root") or r"X:\Mariage_Alexandra_Lucas"
    gateway.save_config(self.config)
    if not self.config["admin_password"] or not self.config["dj_password"]:
        messagebox.showwarning(gateway.APP_NAME, "Renseignez les deux mots de passe avant de démarrer."); return
    if self.server: return
    try:
        ensure_v24_tree(self.config)
        self.server = gateway.GatewayServer(("127.0.0.1", gateway.PORT), V24Handler, self.config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.status.config(text="● Passerelle V2.4 active — port 8788", fg="#74d3ae")
        gateway.log("Passerelle mariage V2.4 démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None; messagebox.showerror(gateway.APP_NAME, f"Démarrage impossible :\n{exc}")


gateway.GatewayUI.start = start_v24

if __name__ == "__main__":
    gateway.GatewayUI().run()
