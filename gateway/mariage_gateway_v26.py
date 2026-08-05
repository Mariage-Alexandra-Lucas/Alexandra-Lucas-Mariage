from __future__ import annotations

import cgi
import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from tkinter import messagebox
from urllib.parse import urlparse

import mariage_gateway as gateway
import mariage_gateway_v2 as v2
import mariage_gateway_v24 as v24
import mariage_gateway_v25 as v25

gateway.PORT = 8788
gateway.VERSION = "2.7.0"
WEB_ORIGIN = "https://mariage-alexandra-lucas.github.io"
PARIS = timezone(timedelta(hours=2), "Europe/Paris")
PAIR_AT = datetime(2026, 8, 29, 15, 0, tzinfo=PARIS)
TEAM_AT = datetime(2026, 8, 29, 15, 45, tzinfo=PARIS)
TABLE_GAMES_AT = datetime(2026, 8, 29, 18, 0, tzinfo=PARIS)
GROUP_LOCK = threading.RLock()


def event_now() -> datetime:
    # L'heure officielle est celle du PC passerelle. astimezone() utilise
    # directement le fuseau configuré dans Windows et ne dépend pas de tzdata.
    return datetime.now().astimezone()


def default_groups() -> dict:
    return {"pairs": [], "teams": [], "updatedAt": None}


def load_groups(config: dict) -> dict:
    value = v24.read_store(config, "manual-groups", default_groups())
    value.setdefault("pairs", []); value.setdefault("teams", [])
    return value


def save_groups(config: dict, value: dict) -> None:
    value["updatedAt"] = v24.now()
    v24.write_store(config, "manual-groups", value)


def validate_pairs(raw: list) -> list:
    if not isinstance(raw, list):
        raise ValueError("Liste de binômes invalide.")
    names, members, result = set(), set(), []
    valid_users = {u["name"] for u in gateway.USERS if u.get("role") != "dj"}
    for index, item in enumerate(raw, 1):
        name = str(item.get("name", "")).strip()[:60]
        people = [str(x).strip() for x in item.get("members", []) if str(x).strip()]
        if not name or name in names:
            raise ValueError(f"Nom manquant ou utilisé deux fois pour le binôme {index}.")
        if len(people) != 2 or people[0] == people[1] or any(x not in valid_users for x in people):
            raise ValueError(f"Le binôme {name} doit contenir deux invités différents.")
        if any(x in members for x in people):
            raise ValueError(f"Un invité du binôme {name} appartient déjà à un autre binôme.")
        names.add(name); members.update(people)
        result.append({"id": f"pair-{uuid.uuid4().hex[:10]}", "name": name, "members": people})
    return result


def validate_teams(raw: list, pairs: list) -> list:
    if not isinstance(raw, list):
        raise ValueError("Liste d’équipes invalide.")
    pair_names = {p["name"] for p in pairs}; used, result = set(), []
    for index, item in enumerate(raw, 1):
        name = str(item.get("name", "")).strip()[:60] or f"Équipe {index}"
        selected = [str(x).strip() for x in item.get("pairs", []) if str(x).strip()]
        if len(selected) != 2 or selected[0] == selected[1] or any(x not in pair_names for x in selected):
            raise ValueError(f"L’équipe {name} doit contenir exactement deux binômes différents.")
        if any(x in used for x in selected):
            raise ValueError(f"Un binôme de l’équipe {name} appartient déjà à une autre équipe.")
        used.update(selected); result.append({"id": f"team-{uuid.uuid4().hex[:10]}", "name": name, "pairs": selected})
    return result


def events_payload(config: dict, user: dict) -> dict:
    groups = load_groups(config)
    proof_pairs = v24.read_store(config, "pairs", [])
    proof_by_name = {p.get("name"): p for p in proof_pairs}
    pairs = []
    for pair in groups["pairs"]:
        proof = proof_by_name.get(pair.get("name"), {})
        pairs.append({**pair, "validated": bool(proof.get("validated")), "photo": proof.get("photo"), "validatedAt": proof.get("validatedAt")})
    person_pair = next((p for p in pairs if user.get("name") in p.get("members", [])), None)
    person_team = None
    if person_pair:
        person_team = next((t for t in groups["teams"] if person_pair.get("name") in t.get("pairs", [])), None)
        if person_team:
            member_pairs = [p for p in pairs if p.get("name") in person_team.get("pairs", [])]
            person_team = {**person_team, "members": [n for p in member_pairs for n in p.get("members", [])]}
    now = event_now()
    admin = user.get("role") == "superadmin"
    return {
        "serverTime": now.isoformat(),
        "gates": {"pair": now >= PAIR_AT, "team": now >= TEAM_AT, "tableGames": now >= TABLE_GAMES_AT},
        "pair": person_pair,
        "team": person_team,
        "pairs": pairs if admin else None,
        "teams": groups["teams"] if admin else None,
        "guests": [u["name"] for u in gateway.USERS if u.get("role") != "dj"],
    }


class V26Handler(v25.V25Handler):
    server_version = "MariageGateway/2.7"

    def _dj_route_allowed(self, route: str) -> bool:
        user = self._user_any()
        if user and user.get("role") == "dj" and not (route == "/api/v25/quiz" or route.startswith("/api/v25/quiz/")):
            self._json({"error": "Le compte DJ est limité à l’animation Elle ou Lui."}, 403)
            return False
        return True

    def do_GET(self):
        route = urlparse(self.path).path
        if not self._dj_route_allowed(route): return
        if route != "/api/v26/events":
            super().do_GET(); return
        user = self._user_required()
        if not user: return
        with GROUP_LOCK:
            self._json(events_payload(self.server.config, user))

    def do_POST(self):
        route = urlparse(self.path).path
        if not self._dj_route_allowed(route): return
        now = event_now()
        if route == "/api/v24/unlock" and now < TABLE_GAMES_AT:
            if not self._user_required(): return
            self._json({"error": "Les jeux des tables seront accessibles à partir de 18h00.", "unlockAt": TABLE_GAMES_AT.isoformat()}, 423); return
        if route == "/api/v24/pair-proof" and now < PAIR_AT:
            if not self._user_required(): return
            self._json({"error": "Le jeu des binômes sera accessible à partir de 15h00."}, 423); return
        if route == "/api/v24/team-proof":
            self._json({"error": "Utilisez la validation de votre équipe attribuée."}, 400); return
        if not route.startswith("/api/v26/"):
            super().do_POST(); return
        user = self._user_required()
        if not user: return
        config = self.server.config
        with GROUP_LOCK:
            try:
                if route == "/api/v26/pairs":
                    if user.get("role") != "superadmin": self._json({"error": "Accès Super Admin requis."}, 403); return
                    data = self._body(); groups = load_groups(config); old_proofs = v24.read_store(config, "pairs", [])
                    old_by_name = {p.get("name"): p for p in old_proofs}
                    pairs = validate_pairs(data.get("pairs", [])); groups["pairs"] = pairs
                    valid_names = {p["name"] for p in pairs}; groups["teams"] = [t for t in groups["teams"] if all(x in valid_names for x in t.get("pairs", []))]
                    save_groups(config, groups)
                    proof_pairs = []
                    for pair in pairs:
                        old = old_by_name.get(pair["name"], {})
                        proof_pairs.append({**pair, "validated": bool(old.get("validated")), "photo": old.get("photo"), "validatedAt": old.get("validatedAt")})
                    v24.write_store(config, "pairs", proof_pairs); self._json(events_payload(config, user)); return
                if route == "/api/v26/teams":
                    if user.get("role") != "superadmin": self._json({"error": "Accès Super Admin requis."}, 403); return
                    data = self._body(); groups = load_groups(config); groups["teams"] = validate_teams(data.get("teams", []), groups["pairs"])
                    save_groups(config, groups); self._json(events_payload(config, user)); return
                if route == "/api/v26/team-proof":
                    if now < TEAM_AT:
                        self._json({"error": "Le jeu des équipes sera accessible à partir de 15h45."}, 423); return
                    groups = load_groups(config); pair = next((p for p in groups["pairs"] if user["name"] in p.get("members", [])), None)
                    team = next((t for t in groups["teams"] if pair and pair["name"] in t.get("pairs", [])), None)
                    if not team: self._json({"error": "Aucune équipe de quatre attribuée."}, 400); return
                    member_pairs = [p for p in groups["pairs"] if p["name"] in team["pairs"]]
                    participants = [n for p in member_pairs for n in p["members"]]
                    form = self._multipart(); field = form["media"] if "media" in form else None
                    if field is None or not getattr(field, "file", None): self._json({"error": "Une photo est obligatoire."}, 400); return
                    filename, _ = v24.save_upload(config, "Equipes", field, v2.safe(team["name"]))
                    proofs = v24.read_store(config, "proofs", [])
                    item = {"id": uuid.uuid4().hex, "kind": "team", "team": team["name"], "pairs": team["pairs"], "participants": participants,
                            "author": user["name"], "text": str(form.getfirst("text", ""))[:300], "photo": v24.media_url("Equipes", filename), "createdAt": v24.now()}
                    proofs.append(item); v24.write_store(config, "proofs", proofs); self._json(item, 201); return
            except ValueError as exc:
                self._json({"error": str(exc)}, 400); return
        self._json({"error": "Route inconnue."}, 404)


def start_v26(self):
    self.save(); self.config["allowed_origin"] = WEB_ORIGIN
    self.config["nas_root"] = self.config.get("nas_root") or r"X:\Mariage_Alexandra_Lucas"; gateway.save_config(self.config)
    if not self.config["admin_password"] or not self.config["dj_password"]:
        messagebox.showwarning(gateway.APP_NAME, "Renseignez les deux mots de passe avant de démarrer."); return
    if self.server: return
    try:
        v24.ensure_v24_tree(self.config)
        self.server = gateway.GatewayServer(("127.0.0.1", gateway.PORT), V26Handler, self.config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.status.config(text="● Passerelle V2.7 active — port 8788", fg="#74d3ae")
        gateway.log("Passerelle mariage V2.7 démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None; messagebox.showerror(gateway.APP_NAME, f"Démarrage impossible :\n{exc}")


gateway.GatewayUI.start = start_v26
if __name__ == "__main__": gateway.GatewayUI().run()
