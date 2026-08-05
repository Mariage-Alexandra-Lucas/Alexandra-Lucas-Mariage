from __future__ import annotations

import threading
from tkinter import messagebox

import mariage_gateway as gateway

# Configuration dédiée à l'application web GitHub Pages.
# Une origine CORS ne contient jamais le chemin /Alexandra-Lucas-Mariage.
gateway.PORT = 8788
gateway.VERSION = "1.5.0"
WEB_ORIGIN = "https://mariage-alexandra-lucas.github.io"

# Migration automatique de l'ancienne configuration V1.4.
config = gateway.load_config()
config["allowed_origin"] = WEB_ORIGIN
config["nas_root"] = config.get("nas_root") or r"X:\Mariage_Alexandra_Lucas"
gateway.save_config(config)


def start_without_admin(self):
    """Démarre sur localhost, sans élévation administrateur."""
    self.save()
    self.config["allowed_origin"] = WEB_ORIGIN
    gateway.save_config(self.config)

    if not self.config["admin_password"] or not self.config["dj_password"]:
        messagebox.showwarning(
            gateway.APP_NAME,
            "Renseignez les deux mots de passe avant de démarrer.",
        )
        return
    if self.server:
        return
    try:
        self.server = gateway.GatewayServer(
            ("127.0.0.1", gateway.PORT),
            gateway.GatewayHandler,
            self.config,
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()
        self.status.config(text="● Passerelle active — port 8788", fg="#74d3ae")
        gateway.log("Passerelle mariage V1.5 démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None
        messagebox.showerror(
            gateway.APP_NAME,
            f"Démarrage impossible :\n{exc}",
        )


gateway.GatewayUI.start = start_without_admin

if __name__ == "__main__":
    gateway.GatewayUI().run()
