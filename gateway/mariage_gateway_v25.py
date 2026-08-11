from __future__ import annotations

import threading
from tkinter import messagebox
from urllib.parse import urlparse

import mariage_gateway as gateway
import mariage_gateway_v24 as v24

gateway.PORT = 8788
gateway.VERSION = "2.5.1"
WEB_ORIGIN = "https://mariage-alexandra-lucas.github.io"
TABLES = ["Guadeloupe", "Île Maurice", "Maldives", "Mexique"]
QUIZ_LOCK = threading.RLock()


def default_quiz() -> dict:
    return {
        "current": -1,
        "questions": [
            {"number": index + 1, "text": "", "answer": "elle", "status": "idle", "responses": {}}
            for index in range(15)
        ],
        "adjustments": {table: 0 for table in TABLES},
        "updatedAt": None,
    }


def load_quiz(config: dict) -> dict:
    quiz = v24.read_store(config, "quiz-dj", default_quiz())
    if not isinstance(quiz.get("questions"), list) or len(quiz["questions"]) != 15:
        quiz = default_quiz()
    quiz.setdefault("adjustments", {table: 0 for table in TABLES})
    return quiz


def save_quiz(config: dict, quiz: dict) -> None:
    quiz["updatedAt"] = v24.now()
    v24.write_store(config, "quiz-dj", quiz)


def reset_round(quiz: dict) -> None:
    for question in quiz["questions"]:
        question["status"] = "idle"
        question["responses"] = {}
    quiz["current"] = -1
    quiz["adjustments"] = {table: 0 for table in TABLES}


def open_question(quiz: dict, index: int) -> None:
    if not 0 <= index < 15 or not quiz["questions"][index].get("text"):
        raise ValueError("Question non configurée.")
    previous = int(quiz.get("current", -1))
    if 0 <= previous < 15 and previous != index and quiz["questions"][previous].get("status") == "open":
        quiz["questions"][previous]["status"] = "closed"
    quiz["current"] = index
    quiz["questions"][index]["status"] = "open"
    quiz["questions"][index]["responses"] = {}


def scores(quiz: dict) -> dict:
    result = {table: int(quiz.get("adjustments", {}).get(table, 0)) for table in TABLES}
    for question in quiz["questions"]:
        if question.get("status") != "revealed":
            continue
        correct = question.get("answer")
        for table, response in question.get("responses", {}).items():
            if table in result and response.get("answer") == correct:
                result[table] += 1
    return result


def quiz_payload(config: dict, user: dict) -> dict:
    quiz = load_quiz(config)
    current_index = int(quiz.get("current", -1))
    current = quiz["questions"][current_index] if 0 <= current_index < 15 else None
    role = user.get("role")
    controller = role in {"superadmin", "dj"}
    payload = {
        "currentIndex": current_index,
        "current": None,
        "scores": scores(quiz),
        "tables": TABLES,
        "canControl": controller,
        "canConfigure": role == "superadmin",
        "updatedAt": quiz.get("updatedAt"),
    }
    if current:
        table = user.get("table")
        payload["current"] = {
            "number": current["number"],
            "text": current["text"],
            "status": current.get("status", "idle"),
            "tableResponse": current.get("responses", {}).get(table) if table else None,
            "responsesCount": len(current.get("responses", {})),
            "responses": current.get("responses", {}) if controller else None,
            "correctAnswer": current.get("answer") if current.get("status") == "revealed" or controller else None,
        }
    if role == "superadmin":
        payload["questions"] = quiz["questions"]
        payload["adjustments"] = quiz.get("adjustments", {})
    elif role == "dj":
        payload["questions"] = [
            {"number": q["number"], "text": q["text"], "status": q.get("status", "idle")}
            for q in quiz["questions"]
        ]
    return payload


class V25Handler(v24.V24Handler):
    server_version = "MariageGateway/2.5.1"

    def do_GET(self):
        route = urlparse(self.path).path
        if route != "/api/v25/quiz":
            super().do_GET(); return
        user = self._user_required()
        if not user:
            return
        with QUIZ_LOCK:
            self._json(quiz_payload(self.server.config, user))

    def do_POST(self):
        route = urlparse(self.path).path
        if not route.startswith("/api/v25/"):
            super().do_POST(); return
        user = self._user_required()
        if not user:
            return
        config = self.server.config
        role = user.get("role")
        data = self._body()
        with QUIZ_LOCK:
            quiz = load_quiz(config)
            if route == "/api/v25/quiz/config":
                if role != "superadmin":
                    self._json({"error": "Accès Super Admin requis."}, 403); return
                questions = data.get("questions", [])
                if not isinstance(questions, list) or len(questions) != 15:
                    self._json({"error": "Le quiz doit contenir exactement 15 questions."}, 400); return
                cleaned = []
                for index, item in enumerate(questions):
                    text = str(item.get("text", "")).strip()[:280]
                    answer = str(item.get("answer", "")).lower()
                    if not text:
                        self._json({"error": f"La question {index + 1} est vide."}, 400); return
                    if answer not in {"elle", "lui"}:
                        self._json({"error": f"Réponse invalide pour la question {index + 1}."}, 400); return
                    cleaned.append({"number": index + 1, "text": text, "answer": answer, "status": "idle", "responses": {}})
                quiz["questions"] = cleaned
                reset_round(quiz)
                try:
                    save_quiz(config, quiz)
                except OSError as exc:
                    self._json({"error": f"Impossible d’enregistrer les questions sur le NAS : {exc}"}, 503); return
                self._json(quiz_payload(config, user)); return
            if route == "/api/v25/quiz/control":
                if role not in {"superadmin", "dj"}:
                    self._json({"error": "Commande réservée au DJ et aux mariés."}, 403); return
                action = str(data.get("action", ""))
                try:
                    if action == "launch":
                        reset_round(quiz)
                        open_question(quiz, 0)
                        quiz["startedAt"] = v24.now()
                    elif action == "start":
                        open_question(quiz, int(data.get("index", 0)))
                    elif action == "next":
                        current = int(quiz.get("current", -1))
                        index = int(data.get("index", current + 1))
                        if current < 0:
                            index = 0
                        if current >= 0 and quiz["questions"][current].get("status") != "revealed":
                            self._json({"error": "Affichez d’abord la bonne réponse avant de passer à la question suivante."}, 409); return
                        open_question(quiz, index)
                    elif action == "close":
                        index = int(quiz.get("current", -1))
                        if not 0 <= index < 15:
                            self._json({"error": "Aucune question active."}, 400); return
                        if quiz["questions"][index].get("status") != "open":
                            self._json({"error": "Les votes ne sont pas ouverts."}, 409); return
                        quiz["questions"][index]["status"] = "closed"
                    elif action == "reveal":
                        index = int(quiz.get("current", -1))
                        if not 0 <= index < 15:
                            self._json({"error": "Aucune question active."}, 400); return
                        if quiz["questions"][index].get("status") not in {"closed", "revealed"}:
                            self._json({"error": "Clôturez d’abord les votes."}, 409); return
                        quiz["questions"][index]["status"] = "revealed"
                    elif action == "correct":
                        index = int(quiz.get("current", -1))
                        answer = str(data.get("answer", "")).lower()
                        if not 0 <= index < 15:
                            self._json({"error": "Aucune question active."}, 400); return
                        if answer not in {"elle", "lui"}:
                            self._json({"error": "Choisissez Elle ou Lui."}, 400); return
                        quiz["questions"][index]["answer"] = answer
                    elif action == "reset":
                        reset_round(quiz)
                    else:
                        self._json({"error": "Commande inconnue."}, 400); return
                except (ValueError, TypeError) as exc:
                    self._json({"error": str(exc)}, 400); return
                save_quiz(config, quiz); self._json(quiz_payload(config, user)); return
            if route == "/api/v25/quiz/answer":
                table = user.get("table")
                if table not in TABLES:
                    self._json({"error": "Aucune table associée à ce compte."}, 403); return
                index = int(quiz.get("current", -1))
                if not 0 <= index < 15 or quiz["questions"][index].get("status") != "open":
                    self._json({"error": "Les réponses sont fermées."}, 423); return
                answer = str(data.get("answer", "")).lower()
                if answer not in {"elle", "lui"}:
                    self._json({"error": "Choisissez Elle ou Lui."}, 400); return
                quiz["questions"][index].setdefault("responses", {})[table] = {
                    "answer": answer, "updatedBy": user["name"], "updatedAt": v24.now()
                }
                save_quiz(config, quiz); self._json(quiz_payload(config, user)); return
            if route == "/api/v25/quiz/score":
                if role != "superadmin":
                    self._json({"error": "Correction réservée au Super Admin."}, 403); return
                table = str(data.get("table", "")); delta = int(data.get("delta", 0))
                if table not in TABLES or delta not in {-1, 1}:
                    self._json({"error": "Correction invalide."}, 400); return
                quiz.setdefault("adjustments", {})[table] = int(quiz["adjustments"].get(table, 0)) + delta
                save_quiz(config, quiz); self._json(quiz_payload(config, user)); return
        self._json({"error": "Route inconnue."}, 404)


def start_v25(self):
    self.save()
    self.config["allowed_origin"] = WEB_ORIGIN
    self.config["nas_root"] = self.config.get("nas_root") or r"X:\Mariage_Alexandra_Lucas"
    gateway.save_config(self.config)
    if not self.config["admin_password"] or not self.config["dj_password"]:
        messagebox.showwarning(gateway.APP_NAME, "Renseignez les deux mots de passe avant de démarrer."); return
    if self.server: return
    try:
        v24.ensure_v24_tree(self.config)
        self.server = gateway.GatewayServer(("127.0.0.1", gateway.PORT), V25Handler, self.config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.status.config(text="● Passerelle V2.5.1 active — port 8788", fg="#74d3ae")
        gateway.log("Passerelle mariage V2.5.1 démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None; messagebox.showerror(gateway.APP_NAME, f"Démarrage impossible :\n{exc}")


gateway.GatewayUI.start = start_v25

if __name__ == "__main__":
    gateway.GatewayUI().run()
