from __future__ import annotations

import threading
from tkinter import messagebox

import mariage_gateway as gateway

# Port dédié à la passerelle mariage. La passerelle ERP ASM conserve le port 8787.
gateway.PORT = 8788
gateway.VERSION = "1.4.0"


def start_without_admin(self):
    """Démarre uniquement sur localhost, sans élévation administrateur."""
    self.save()
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
        gateway.log("Passerelle mariage démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None
        messagebox.showerror(
            gateway.APP_NAME,
            f"Démarrage impossible :\n{exc}",
        )


gateway.GatewayUI.start = start_without_admin

if __name__ == "__main__":
    gateway.GatewayUI().run()
