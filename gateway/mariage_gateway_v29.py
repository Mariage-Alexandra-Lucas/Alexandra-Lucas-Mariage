from __future__ import annotations

import subprocess
import tempfile
import threading
from collections import defaultdict, deque
from pathlib import Path
from tkinter import messagebox
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
import imageio_ffmpeg

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

import mariage_gateway as gateway
import mariage_gateway_v2 as v2
import mariage_gateway_v24 as v24
import mariage_gateway_v26 as v26


gateway.PORT = 8788
gateway.VERSION = "2.9.0"
WEB_ORIGIN = "https://mariage-alexandra-lucas.github.io"
VIDEO_LOCK = threading.RLock()
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VIDEO_W, VIDEO_H = 720, 1280
PHOTO_SECONDS = 3.6


def _font(size: int, italic: bool = False):
    names = [
        r"C:\Windows\Fonts\georgiai.ttf" if italic else r"C:\Windows\Fonts\georgia.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for name in names:
        if Path(name).exists():
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _media_path(config: dict, media_url: str | None) -> Path | None:
    if not media_url:
        return None
    parsed = urlparse(media_url)
    if parsed.path == "/api/v24/media":
        query = parse_qs(parsed.query)
        folder = v2.safe(query.get("folder", [""])[0])
        filename = v2.safe(query.get("file", [""])[0])
        path = v24.v24_root(config) / "Medias" / folder / filename
        return path if path.suffix.lower() in IMAGE_EXTS else None
    if parsed.path == "/api/media":
        query = parse_qs(parsed.query)
        kind = query.get("kind", [""])[0]
        owner = v2.safe(query.get("owner", [""])[0])
        filename = v2.safe(query.get("file", [""])[0])
        if Path(filename).suffix.lower() not in IMAGE_EXTS:
            return None
        if kind == "story":
            return v2.root(config) / "Photos" / "Stories" / filename
        if kind == "photo":
            return v2.root(config) / "Photos" / "Privees" / owner / filename
    return None


def _candidate(path: Path | None, owner: str, source: str, created_at: str = "", participants=None, text: str = ""):
    if not path or path.suffix.lower() not in IMAGE_EXTS or not path.exists() or not path.is_file():
        return None
    return {
        "path": path,
        "owner": owner or "Invités",
        "source": source,
        "createdAt": created_at or "",
        "participants": list(participants or []),
        "text": text or "",
    }


def _private_and_story_candidates(config: dict, allowed_names: set[str] | None) -> list[dict]:
    result = []
    private_root = v2.root(config) / "Photos" / "Privees"
    if private_root.exists():
        for meta_file in private_root.glob("*/*.json"):
            meta = v2.read_meta(meta_file)
            if not meta:
                continue
            owner = str(meta.get("owner", ""))
            if allowed_names is not None and owner not in allowed_names:
                continue
            item = _candidate(meta_file.parent / str(meta.get("filename", "")), owner, "personal", str(meta.get("createdAt", "")))
            if item:
                result.append(item)
    stories_root = v2.root(config) / "Photos" / "Stories"
    if stories_root.exists():
        for meta_file in stories_root.glob("*.json"):
            meta = v2.read_meta(meta_file)
            if not meta:
                continue
            owner = str(meta.get("owner", ""))
            if allowed_names is not None and owner not in allowed_names:
                continue
            item = _candidate(stories_root / str(meta.get("filename", "")), owner, "story", str(meta.get("createdAt", "")), text=str(meta.get("comment", "")))
            if item:
                result.append(item)
    return result


def _animation_candidates(config: dict, allowed_names: set[str] | None) -> list[dict]:
    result = []
    for item in v24.read_store(config, "guestbook", []):
        owner = str(item.get("author", ""))
        participants = [str(x) for x in item.get("participants", [])]
        if allowed_names is not None and owner not in allowed_names and not allowed_names.intersection(participants):
            continue
        path = _media_path(config, item.get("media") or item.get("photo"))
        candidate = _candidate(path, owner, "guestbook", str(item.get("createdAt", "")), participants, str(item.get("text", "")))
        if candidate:
            result.append(candidate)

    pairs = v24.read_store(config, "pairs", [])
    for pair in pairs:
        members = [str(x) for x in pair.get("members", [])]
        if allowed_names is not None and not allowed_names.intersection(members):
            continue
        path = _media_path(config, pair.get("photo"))
        candidate = _candidate(path, " & ".join(members), "pair", str(pair.get("validatedAt", "")), members)
        if candidate:
            result.append(candidate)

    for proof in v24.read_store(config, "proofs", []):
        participants = [str(x) for x in proof.get("participants", [])]
        owner = str(proof.get("author", ""))
        if allowed_names is not None and owner not in allowed_names and not allowed_names.intersection(participants):
            continue
        source = str(proof.get("kind", "challenge"))
        if source not in {"pair", "team", "challenge"}:
            source = "challenge"
        path = _media_path(config, proof.get("photo") or proof.get("media"))
        candidate = _candidate(path, owner, source, str(proof.get("createdAt", "")), participants, str(proof.get("text", "")))
        if candidate:
            result.append(candidate)
    return result


def _group_for_user(config: dict, user_name: str) -> tuple[list[str], list[str]]:
    groups = v26.load_groups(config)
    pair = next((p for p in groups.get("pairs", []) if user_name in p.get("members", [])), None)
    pair_members = [str(x) for x in (pair or {}).get("members", [])]
    team_members = []
    if pair:
        team = next((t for t in groups.get("teams", []) if pair.get("name") in t.get("pairs", [])), None)
        if team:
            pair_names = set(team.get("pairs", []))
            team_members = [str(n) for p in groups.get("pairs", []) if p.get("name") in pair_names for n in p.get("members", [])]
    return pair_members, team_members


def collect_candidates(config: dict, user: dict) -> tuple[list[dict], int, set[str]]:
    global_video = user.get("role") == "superadmin" and user.get("name") in {"Alexandra", "Lucas"}
    if global_video:
        allowed = None
        max_photos = 50
        people = {u["name"] for u in gateway.USERS if u.get("role") != "dj"}
    else:
        pair_members, team_members = _group_for_user(config, str(user.get("name", "")))
        people = set(team_members or pair_members or [str(user.get("name", ""))])
        people.add(str(user.get("name", "")))
        allowed = people
        max_photos = 15
    candidates = _private_and_story_candidates(config, allowed) + _animation_candidates(config, allowed)
    return candidates, max_photos, people


def _dhash(path: Path) -> int | None:
    try:
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            px = list(image.getdata())
        value = 0
        for y in range(8):
            for x in range(8):
                value = (value << 1) | int(px[y * 9 + x] > px[y * 9 + x + 1])
        return value
    except Exception:
        return None


def _distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def select_diverse(candidates: list[dict], max_photos: int) -> list[dict]:
    unique_paths = {}
    for item in candidates:
        unique_paths[str(item["path"]).lower()] = item
    items = list(unique_paths.values())
    for item in items:
        item["hash"] = _dhash(item["path"])
    items = [x for x in items if x["hash"] is not None]
    items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

    buckets: dict[str, deque] = defaultdict(deque)
    for item in items:
        key = item.get("owner") or item.get("source") or "Invités"
        buckets[key].append(item)
    selected, hashes = [], []
    keys = deque(sorted(buckets, key=lambda k: (-len(buckets[k]), k.lower())))
    while keys and len(selected) < max_photos:
        key = keys.popleft()
        bucket = buckets[key]
        picked = None
        while bucket:
            item = bucket.popleft()
            if all(_distance(item["hash"], h) > 8 for h in hashes):
                picked = item
                break
        if picked:
            selected.append(picked); hashes.append(picked["hash"])
        if bucket:
            keys.append(key)

    minimum = min(10, len(items), max_photos)
    if len(selected) < minimum:
        for item in items:
            if item in selected:
                continue
            if all(_distance(item["hash"], h) > 3 for h in hashes):
                selected.append(item); hashes.append(item["hash"])
                if len(selected) >= minimum or len(selected) >= max_photos:
                    break
    return selected[:max_photos]


def automatic_comment(item: dict, index: int, global_video: bool, viewer: str) -> str:
    owner = item.get("owner") or "les invités"
    participants = [p for p in item.get("participants", []) if p]
    source = item.get("source")
    if global_video:
        templates = {
            "pair": ["Un joli moment de complicité à deux.", "Les binômes ont créé de beaux souvenirs."],
            "team": ["À quatre, les souvenirs sont encore plus beaux.", "Une équipe réunie pour un instant unique."],
            "challenge": ["Défi relevé, sourire immortalisé.", "Un défi devenu un souvenir de notre journée."],
            "story": [f"Un instant partagé par {owner}.", f"Le mariage vu par {owner}."],
            "guestbook": [f"Un souvenir laissé par {owner} pour Alexandra & Lucas.", "Quelques secondes de bonheur à garder longtemps."],
            "personal": [f"Un regard sur la journée signé {owner}.", f"Un souvenir capturé par {owner}."],
        }
    else:
        if source == "personal" and owner == viewer:
            return ["Un de tes souvenirs de cette belle journée.", "Un instant que tu as choisi de garder.", "Ta journée, ton regard, ton souvenir."][index % 3]
        if source == "pair":
            return ["Votre binôme réuni pour un joli souvenir.", "À deux, un moment à garder précieusement."][index % 2]
        if source == "team":
            return ["Votre équipe de quatre au complet.", "Un souvenir partagé avec votre équipe."][index % 2]
        if participants:
            names = ", ".join(participants[:4])
            return f"Un moment partagé avec {names}."
        templates = {
            "story": [f"Un instant capturé par {owner}.", f"Le mariage à travers le regard de {owner}."],
            "guestbook": [f"Un souvenir partagé par {owner}.", "Un petit morceau de cette belle journée."],
            "challenge": ["Un défi relevé ensemble.", "Mission accomplie, souvenir assuré."],
            "personal": [f"Un souvenir capturé par {owner}.", f"Un beau moment partagé avec {owner}."],
        }
    choices = templates.get(source, ["Un beau souvenir du mariage d’Alexandra & Lucas."])
    return choices[index % len(choices)]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:3]


def render_frame(item: dict, comment: str, destination: Path, global_video: bool):
    with Image.open(item["path"]) as opened:
        source = ImageOps.exif_transpose(opened).convert("RGB")
    background = ImageOps.fit(source, (VIDEO_W, VIDEO_H), method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(28)).point(lambda p: int(p * 0.62))
    canvas = background.convert("RGBA")

    max_w, max_h = VIDEO_W - 72, VIDEO_H - 290
    foreground = source.copy()
    foreground.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    x = (VIDEO_W - foreground.width) // 2
    y = max(54, (VIDEO_H - 230 - foreground.height) // 2)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((x - 8, y - 8, x + foreground.width + 8, y + foreground.height + 8), 24, fill=(0, 0, 0, 85))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    canvas.alpha_composite(shadow)
    canvas.paste(foreground, (x, y))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((36, VIDEO_H - 236, VIDEO_W - 36, VIDEO_H - 42), 28, fill=(20, 24, 32, 188))
    title_font = _font(24, italic=True)
    comment_font = _font(34, italic=True)
    small_font = _font(20)
    title = "Livre d’or d’Alexandra & Lucas" if global_video else "Souvenir du mariage d’Alexandra & Lucas"
    draw.text((64, VIDEO_H - 214), title, font=title_font, fill=(244, 201, 139, 255))
    lines = _wrap_text(draw, comment, comment_font, VIDEO_W - 128)
    yy = VIDEO_H - 174
    for line in lines:
        draw.text((64, yy), line, font=comment_font, fill=(255, 255, 255, 255))
        yy += 43
    draw.text((64, VIDEO_H - 70), "29 août 2026", font=small_font, fill=(215, 220, 228, 255))
    canvas.alpha_composite(overlay)
    canvas.convert("RGB").save(destination, "JPEG", quality=91, optimize=True)


def generate_video(config: dict, user: dict) -> tuple[Path, int]:
    candidates, max_photos, _ = collect_candidates(config, user)
    selected = select_diverse(candidates, max_photos)
    if not selected:
        raise ValueError("Aucune photo disponible pour créer votre vidéo souvenir.")
    global_video = user.get("role") == "superadmin" and user.get("name") in {"Alexandra", "Lucas"}
    video_dir = v24.v24_root(config) / "Videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    video_name = "Livre-Or-Alexandra-Lucas.mp4" if global_video else f"Souvenir-{v2.safe(str(user.get('name', 'invite')))}.mp4"
    output = video_dir / video_name
    newest = max((x["path"].stat().st_mtime for x in selected), default=0)
    if output.exists() and output.stat().st_mtime >= newest:
        return output, len(selected)

    temp_root = v2.root(config) / "Temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mariage-video-", dir=str(temp_root)) as temp_name:
        temp = Path(temp_name)
        frames = []
        for index, item in enumerate(selected):
            frame = temp / f"frame-{index:03d}.jpg"
            render_frame(item, automatic_comment(item, index, global_video, str(user.get("name", ""))), frame, global_video)
            frames.append(frame)
        concat = temp / "concat.txt"
        rows = []
        for frame in frames:
            rows.append(f"file '{str(frame)}'")
            rows.append(f"duration {PHOTO_SECONDS}")
        rows.append(f"file '{str(frames[-1])}'")
        concat.write_text("\n".join(rows), encoding="utf-8")
        temp_output = output.with_suffix(".tmp.mp4")
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat),
            "-vf", f"scale={VIDEO_W}:{VIDEO_H},format=yuv420p",
            "-r", "25", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-movflags", "+faststart", str(temp_output),
        ]
        subprocess.run(cmd, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        temp_output.replace(output)
    return output, len(selected)


class V29Handler(v26.V26Handler):
    server_version = "MariageGateway/2.9.0"

    def do_GET(self):
        route = urlparse(self.path).path
        if route != "/api/v29/souvenir.mp4":
            super().do_GET(); return
        user = self._user_required()
        if not user:
            return
        if user.get("role") == "dj":
            self._json({"error": "Le compte DJ ne possède pas de livre d’or vidéo."}, 403); return
        try:
            with VIDEO_LOCK:
                video, photo_count = generate_video(self.server.config, user)
            data = video.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Disposition", f'attachment; filename="{video.name}"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Selected-Photos", str(photo_count))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", WEB_ORIGIN)
            self.end_headers(); self.wfile.write(data)
        except ValueError as exc:
            self._json({"error": str(exc)}, 409)
        except Exception as exc:
            gateway.log(f"Erreur génération vidéo : {exc}")
            self._json({"error": "La vidéo souvenir n’a pas pu être générée. Vérifiez les photos et réessayez."}, 500)


def start_v29(self):
    self.save(); self.config["allowed_origin"] = WEB_ORIGIN
    self.config["nas_root"] = self.config.get("nas_root") or r"X:\Mariage_Alexandra_Lucas"; gateway.save_config(self.config)
    if not self.config["admin_password"] or not self.config["dj_password"]:
        messagebox.showwarning(gateway.APP_NAME, "Renseignez les deux mots de passe avant de démarrer."); return
    if self.server: return
    try:
        v24.ensure_v24_tree(self.config)
        (v2.root(self.config) / "Temp").mkdir(parents=True, exist_ok=True)
        self.server = gateway.GatewayServer(("127.0.0.1", gateway.PORT), V29Handler, self.config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.status.config(text="● Passerelle V2.9.0 active — vidéo souvenir MP4", fg="#74d3ae")
        gateway.log("Passerelle mariage V2.9.0 démarrée sur 127.0.0.1:8788")
    except Exception as exc:
        self.server = None; messagebox.showerror(gateway.APP_NAME, f"Démarrage impossible :\n{exc}")


gateway.GatewayUI.start = start_v29
if __name__ == "__main__": gateway.GatewayUI().run()
