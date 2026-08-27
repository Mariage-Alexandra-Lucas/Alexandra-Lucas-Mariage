from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

import mariage_gateway as gateway
import mariage_gateway_v2 as v2
import mariage_gateway_v24 as v24
import mariage_gateway_v29 as v29


def generate_video_windows(config: dict, user: dict) -> tuple[Path, int]:
    """Version Windows de la génération : FFmpeg concat exige des chemins avec / dans le manifeste."""
    candidates, max_photos, _ = v29.collect_candidates(config, user)
    selected = v29.select_diverse(candidates, max_photos)
    if not selected:
        raise ValueError("Aucune photo disponible pour créer votre vidéo souvenir.")

    global_video = user.get("role") == "superadmin" and user.get("name") in {"Alexandra", "Lucas"}
    video_dir = v24.v24_root(config) / "Videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    video_name = "Livre-Or-Alexandra-Lucas.mp4" if global_video else f"Souvenir-{v2.safe(str(user.get('name', 'invite')))}.mp4"
    output = video_dir / video_name

    newest = max((item["path"].stat().st_mtime for item in selected), default=0)
    if output.exists() and output.stat().st_mtime >= newest:
        return output, len(selected)

    temp_root = v2.root(config) / "Temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mariage-video-", dir=str(temp_root)) as temp_name:
        temp = Path(temp_name)
        frames: list[Path] = []
        for index, item in enumerate(selected):
            frame = temp / f"frame-{index:03d}.jpg"
            comment = v29.automatic_comment(item, index, global_video, str(user.get("name", "")))
            v29.render_frame(item, comment, frame, global_video)
            frames.append(frame)

        concat = temp / "concat.txt"
        rows: list[str] = []
        for frame in frames:
            rows.append(f"file '{frame.as_posix()}'")
            rows.append(f"duration {v29.PHOTO_SECONDS}")
        rows.append(f"file '{frames[-1].as_posix()}'")
        concat.write_text("\n".join(rows), encoding="utf-8")

        temp_output = output.with_suffix(".tmp.mp4")
        command = [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat),
            "-vf", f"scale={v29.VIDEO_W}:{v29.VIDEO_H},format=yuv420p",
            "-r", "25", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-movflags", "+faststart", str(temp_output),
        ]
        subprocess.run(command, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        temp_output.replace(output)

    return output, len(selected)


v29.generate_video = generate_video_windows


if __name__ == "__main__":
    gateway.GatewayUI().run()
