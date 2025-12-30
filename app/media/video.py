import subprocess
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont


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

    concat_file = output_path.parent / "concat.txt"
    lines = []
    for img in images:
        lines.append(f"file '{img.as_posix()}'")
        lines.append(f"duration {seconds_per_image}")
    # FFmpeg requires last file listed again without duration
    lines.append(f"file '{images[-1].as_posix()}'")
    concat_file.write_text("\n".join(lines))

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-vsync",
        "vfr",
        "-r",
        str(fps),
    ]
    if audio_path:
        cmd += ["-i", str(audio_path), "-shortest"]
    if captions_path:
        cmd += ["-vf", f"subtitles={captions_path}"]
    cmd += [str(output_path)]

    subprocess.run(cmd, check=True)
