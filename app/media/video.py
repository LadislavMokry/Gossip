import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings


def create_placeholder_images(
    scenes: Sequence[str],
    output_dir: Path,
    size: tuple[int, int] = (1080, 1920),
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    images: list[Path] = []
    for idx, text in enumerate(scenes):
        img = Image.new("RGB", size, color=(20, 20, 20))
        draw = ImageDraw.Draw(img)
        caption = (text or f"Scene {idx + 1}")[:200]
        draw.text((60, 120), caption, fill=(255, 255, 255))
        path = output_dir / f"scene_{idx+1:02d}.png"
        img.save(path)
        images.append(path)
    return images


def assemble_video(
    images: Sequence[Path],
    audio_path: Path | None,
    output_path: Path,
    fps: int = 30,
    seconds_per_image: int = 6,
    captions_path: Path | None = None,
) -> None:
    if not images:
        raise ValueError("No images to assemble")

    settings = get_settings()
    ffmpeg_bin = settings.ffmpeg_path or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg not found. Set FFMPEG_PATH or add ffmpeg to PATH.")

    work_dir = images[0].parent
    concat_file = work_dir / "concat.txt"
    lines = []
    for img in images:
        lines.append(f"file '{img.name}'")
        lines.append(f"duration {seconds_per_image}")
    # FFmpeg requires last file listed again without duration
    lines.append(f"file '{images[-1].name}'")
    concat_file.write_text("\n".join(lines))

    audio_arg = str(audio_path.resolve()) if audio_path else None
    captions_arg = str(captions_path.resolve()) if captions_path else None
    if audio_path and audio_path.parent == work_dir:
        audio_arg = audio_path.name
    if captions_path and captions_path.parent == work_dir:
        captions_arg = captions_path.name

    cmd = [
        ffmpeg_bin,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        "concat.txt",
        "-vsync",
        "vfr",
        "-r",
        str(fps),
    ]
    if audio_path:
        cmd += ["-i", audio_arg, "-shortest"]
    if captions_path:
        cmd += ["-vf", f"subtitles={captions_arg}"]
    cmd += [str(output_path.resolve())]

    subprocess.run(cmd, check=True, cwd=work_dir)
