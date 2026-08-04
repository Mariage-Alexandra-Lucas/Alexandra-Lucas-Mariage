from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, Entry, Frame, Label, StringVar, Tk, messagebox
from urllib.parse import urlparse

APP_NAME = "Passerelle Mariage Alexandra & Lucas"
VERSION = "1.0.0"
PORT = 8787
UNLOCK_AT = datetime.fromisoformat("2026-08-29T18:00:00+02:00")
APP_URL = "https://alpesex.github.io/Alexandra-Lucas-Mariage/"

TABLES = {
    "Guadeloupe": ["Kevin", "Marie-Jo", "Marc", "Sylvie", "Louise", "Joseph", "Boris", "Méline", "Morgane"],
    "Île Maurice": ["Sophie D", "Michel D", "Éliane", "Gérard", "Michel T", "Sophie T", "Nino", "Nathalie"],
    "Maldives": ["Alexandra", "Lucas", "Maxime B", "Roman", "Marine", "Clémence", "Alexandre", "Khoil", "Michel A"],
    "Mexique": ["Quentin", "Maxime P", "Lucas B", "Chloé", "Loris", "Nina", "Maxime G", "Florian", "Sarah"],
}


def norm(value: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", value.strip().lower()) if unicodedata.category(c) != "Mn")

USERS = []
for table, names in TABLES.items():
    for name in names:
        USERS.append({"name": name, "table": table, "role": "superadmin" if name in ("Alexandra", "Lucas") else "guest"})
USERS.append({"name": "DJ", "table": None, "role": "dj"})

BASE_DIR = Path(os.getenv("PROGRAMDATA", Path.home())) / "Mariage_Alexandra_Lucas"
CONFIG_PATH = BASE_DIR / "gateway-config.json"
LOG_PATH = BASE_DIR / "gateway.log"


def default_config() -> dict:
    return {
        "nas_root": r"\\192.168.1.131\Mariage_Alexandra_Lucas",
        "admin_password": "",
        "dj_password": "",
        "token_secret": secrets.token_hex(32),
        "allowed_origin": APP_URL.rstrip("/"),
    }


def load_config() -> dict:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        cfg = default_config()
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return cfg
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    merged = default_config()
    merged.update(cfg)
    return merged


def save_config(cfg: dict) -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def log(message: str) -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat(timespec='seconds')} | {message}\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def sign_token(payload: dict, secret: str) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    body = b64(raw)
    sig = b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_token(token: str, secret: str) -> dict | None:
    try:
        body, sig = token.split(".", 1)
        expected = b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "MariageGateway/1.0"

    def _headers(self, status=200, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", self.server.config["allowed_origin"])
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _json(self, data, status=200):
        self._headers(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def _user(self):
        token = self.headers.get("Authorization", "").replace("Bearer ", "", 1)
        return verify_token(token, self.server.config["token_secret"])

    def do_OPTIONS(self):
        self._headers(204)

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/health":
            nas_path = Path(self.server.config["nas_root"])
            nas_ok = nas_path.exists()
            self._json({"ok": True, "version": VERSION, "nasConnected": nas_ok, "serverTime": datetime.now(timezone.utc).isoformat()})
            return
        if route == "/api/time":
            now = datetime.now().astimezone()
            self._json({"serverTime": now.isoformat(), "tableUnlockAt": UNLOCK_AT.isoformat(), "tableUnlocked": now >= UNLOCK_AT})
            return
        if route == "/api/table":
            user = self._user()
            if not user:
                self._json({"error": "Session invalide."}, 401); return
            now = datetime.now().astimezone()
            if now < UNLOCK_AT and user["role"] != "superadmin":
                self._json({"locked": True, "unlockAt": UNLOCK_AT.isoformat()}, 423); return
            if user["role"] == "dj":
                self._json({"table": None, "guests": []}); return
            self._json({"table": user["table"], "guests": TABLES.get(user["table"], [])})
            return
        self._json({"error": "Route inconnue."}, 404)

    def do_POST(self):
        route = urlparse(self.path).path
        if route == "/api/login":
            data = self._body()
            requested = norm(str(data.get("name", "")))
            password = str(data.get("password", ""))
            user = next((u for u in USERS if norm(u["name"]) == requested), None)
            if not user:
                self._json({"error": "Prénom non reconnu."}, 401); return
            cfg = self.server.config
            if user["role"] == "superadmin" and (not cfg["admin_password"] or password != cfg["admin_password"]):
                self._json({"error": "Mot de passe administrateur incorrect."}, 401); return
            if user["role"] == "dj" and (not cfg["dj_password"] or password != cfg["dj_password"]):
                self._json({"error": "Mot de passe DJ incorrect."}, 401); return
            payload = {**user, "exp": int(time.time()) + 86400}
            self._json({"token": sign_token(payload, cfg["token_secret"]), "user": user})
            return
        self._json({"error": "Route inconnue."}, 404)

    def log_message(self, fmt, *args):
        log(fmt % args)


class GatewayServer(ThreadingHTTPServer):
    def __init__(self, address, handler, config):
        super().__init__(address, handler)
        self.config = config


class GatewayUI:
    def __init__(self):
        self.config = load_config()
        self.server = None
        self.thread = None
        self.root = Tk()
        self.root.title(APP_NAME)
        self.root.geometry("720x500")
        self.root.minsize(680, 460)
        self.root.configure(bg="#101827")
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        header = Frame(self.root, bg="#17243a", padx=24, pady=20)
        header.pack(fill=X)
        Label(header, text="ALEXANDRA  &  LUCAS", fg="#f7c98b", bg="#17243a", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        Label(header, text="Passerelle du mariage", fg="white", bg="#17243a", font=("Segoe UI", 25, "bold")).pack(anchor="w")
        Label(header, text=f"Version {VERSION} • NAS 192.168.1.131", fg="#b8c4d9", bg="#17243a", font=("Segoe UI", 10)).pack(anchor="w", pady=(5,0))

        body = Frame(self.root, bg="#101827", padx=24, pady=20)
        body.pack(fill=BOTH, expand=True)

        self.vars = {
            "nas_root": StringVar(value=self.config["nas_root"]),
            "admin_password": StringVar(value=self.config["admin_password"]),
            "dj_password": StringVar(value=self.config["dj_password"]),
        }
        self._field(body, "Dossier réseau du NAS", "nas_root", False)
        self._field(body, "Mot de passe Alexandra / Lucas", "admin_password", True)
        self._field(body, "Mot de passe DJ", "dj_password", True)

        status_box = Frame(body, bg="#17243a", padx=18, pady=14)
        status_box.pack(fill=X, pady=(18, 12))
        self.status = Label(status_box, text="● Passerelle arrêtée", fg="#ff9b9b", bg="#17243a", font=("Segoe UI", 12, "bold"))
        self.status.pack(side=LEFT)
        self.nas_status = Label(status_box, text="NAS non testé", fg="#b8c4d9", bg="#17243a", font=("Segoe UI", 10))
        self.nas_status.pack(side=RIGHT)

        buttons = Frame(body, bg="#101827")
        buttons.pack(fill=X, pady=(4, 0))
        Button(buttons, text="Enregistrer", command=self.save, bg="#f0b46a", fg="#101827", relief="flat", padx=18, pady=10, font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        Button(buttons, text="Démarrer", command=self.start, bg="#74d3ae", fg="#101827", relief="flat", padx=18, pady=10, font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=10)
        Button(buttons, text="Tester le NAS", command=self.test_nas, bg="#31435f", fg="white", relief="flat", padx=18, pady=10).pack(side=LEFT)
        Button(buttons, text="Ouvrir l'application", command=lambda: webbrowser.open(APP_URL), bg="#31435f", fg="white", relief="flat", padx=18, pady=10).pack(side=RIGHT)

        Label(body, text="Adresse locale : http://127.0.0.1:8787/api/health", fg="#7f90aa", bg="#101827", font=("Consolas", 9)).pack(anchor="w", pady=(18,0))
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _field(self, parent, label, key, secret):
        wrap = Frame(parent, bg="#101827")
        wrap.pack(fill=X, pady=6)
        Label(wrap, text=label, fg="#dce5f4", bg="#101827", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        Entry(wrap, textvariable=self.vars[key], show="•" if secret else "", bg="#223149", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 11)).pack(fill=X, ipady=9, pady=(5,0))

    def save(self):
        for key, var in self.vars.items():
            self.config[key] = var.get().strip()
        save_config(self.config)
        messagebox.showinfo(APP_NAME, "Configuration enregistrée.")

    def test_nas(self):
        self.save()
        path = Path(self.config["nas_root"])
        try:
            path.mkdir(parents=True, exist_ok=True)
            test = path / ".gateway-test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            self.nas_status.config(text="NAS connecté", fg="#74d3ae")
        except Exception as exc:
            self.nas_status.config(text="NAS inaccessible", fg="#ff9b9b")
            messagebox.showerror(APP_NAME, f"Impossible d'accéder au NAS :\n{exc}")

    def start(self):
        self.save()
        if not self.config["admin_password"] or not self.config["dj_password"]:
            messagebox.showwarning(APP_NAME, "Renseignez les deux mots de passe avant de démarrer.")
            return
        if self.server:
            return
        try:
            self.server = GatewayServer(("0.0.0.0", PORT), GatewayHandler, self.config)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.status.config(text="● Passerelle active", fg="#74d3ae")
            log("Passerelle démarrée")
        except Exception as exc:
            self.server = None
            messagebox.showerror(APP_NAME, f"Démarrage impossible :\n{exc}")

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    GatewayUI().run()
