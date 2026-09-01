#!/usr/bin/env python3
"""Deterministic Stage 1 renderer for AI News by Carni Shorts.

Input: validated JSON manifest.
Output: vertical 1080x1920 H.264/AAC MP4 with a silent audio track.

Editorial decisions must already exist in the manifest. This renderer only turns
that manifest into the approved Carni Shorts v1 visual format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
HEIGHT = 1920
FPS = 30
BG = (3, 10, 17)
PANEL = (6, 20, 31)
GRID = (12, 62, 91)
BLUE = (46, 167, 255)
BLUE_SOFT = (116, 203, 255)
WHITE = (238, 245, 250)
MUTED = (155, 180, 195)
SAFE_X = 92
SAFE_TOP = 190
SAFE_BOTTOM = 320

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "shorts" / "schema" / "manifest.schema.json"


def fail(message: str) -> None:
    raise SystemExit(message)


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        fail(f"Command failed: {' '.join(cmd)}")


def find_font(bold: bool = False) -> str:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]
        )
    for path in candidates:
        if Path(path).exists():
            return path
    fail("No supported font found. Install DejaVu Sans or Liberation Sans.")


FONT_REGULAR = find_font(False)
FONT_BOLD = find_font(True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size=size)


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        rendered = []
        for err in errors:
            where = ".".join(str(x) for x in err.absolute_path) or "<root>"
            rendered.append(f"{where}: {err.message}")
        fail("Manifest validation failed:\n- " + "\n- ".join(rendered))

    total = sum(float(scene["duration"]) for scene in data["scenes"])
    if not 20 <= total <= 60:
        fail(f"Total duration must be 20–60 seconds, got {total:.2f}s")
    return data


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        box = draw.textbbox((0, 0), test, font=fnt)
        if box[2] - box[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_lines: int, start_size: int, min_size: int) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    size = start_size
    while size >= min_size:
        fnt = font(size, bold=True)
        lines = wrap_lines(draw, text, fnt, max_width)
        if len(lines) <= max_lines:
            return fnt, lines
        size -= 4
    fnt = font(min_size, bold=True)
    return fnt, wrap_lines(draw, text, fnt, max_width)[:max_lines]


def draw_circuit(draw: ImageDraw.ImageDraw, seed: int, scene_index: int) -> None:
    # Deterministic, restrained circuit/grid motif. No randomness at render time.
    offset = (seed + scene_index * 37) % 83
    for y in range(260 + offset, 1540, 170):
        x0 = 70 + ((y + seed) % 140)
        x1 = WIDTH - 70 - ((y + scene_index * 19) % 120)
        draw.line((x0, y, x1, y), fill=GRID, width=2)
        draw.ellipse((x0 - 5, y - 5, x0 + 5, y + 5), outline=BLUE, width=2)
        if (y // 170 + scene_index) % 2 == 0:
            branch_x = x0 + int((x1 - x0) * 0.62)
            draw.line((branch_x, y, branch_x, y + 72), fill=GRID, width=2)
            draw.ellipse((branch_x - 4, y + 68, branch_x + 4, y + 76), fill=BLUE_SOFT)

    for x in range(120 + (offset % 50), WIDTH - 100, 210):
        draw.line((x, 300, x, 1500), fill=(7, 32, 48), width=1)


def draw_header(draw: ImageDraw.ImageDraw, index: int, count: int) -> None:
    draw.text((SAFE_X, SAFE_TOP), "AI NEWS", font=font(34, True), fill=BLUE)
    draw.text((SAFE_X + 190, SAFE_TOP + 4), "BY CARNI", font=font(27, True), fill=WHITE)
    y = SAFE_TOP + 67
    usable = WIDTH - 2 * SAFE_X
    draw.rounded_rectangle((SAFE_X, y, WIDTH - SAFE_X, y + 5), radius=3, fill=(18, 48, 65))
    progress = usable * (index + 1) / count
    draw.rounded_rectangle((SAFE_X, y, SAFE_X + progress, y + 5), radius=3, fill=BLUE)


def draw_scene(manifest: dict, scene: dict, index: int, out_path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    seed = int(hashlib.sha256(manifest["id"].encode("utf-8")).hexdigest()[:8], 16)

    draw_circuit(draw, seed, index)
    draw_header(draw, index, len(manifest["scenes"]))

    # Central translucent-like panel, rendered as a solid dark panel for deterministic output.
    panel_top = 390
    panel_bottom = HEIGHT - SAFE_BOTTOM - 80
    draw.rounded_rectangle(
        (SAFE_X - 18, panel_top, WIDTH - SAFE_X + 18, panel_bottom),
        radius=42,
        fill=PANEL,
        outline=(22, 73, 101),
        width=2,
    )

    kicker = scene.get("kicker") or scene["type"].upper()
    draw.text((SAFE_X + 30, panel_top + 62), kicker.upper(), font=font(31, True), fill=BLUE_SOFT)

    max_text_width = WIDTH - 2 * (SAFE_X + 30)
    start_size = 96 if scene["type"] == "hook" else 76
    max_lines = 4 if scene["type"] == "hook" else 5
    main_font, lines = fit_text(draw, scene["text"], max_text_width, max_lines, start_size, 54)

    line_gap = int(main_font.size * 0.28)
    line_height = main_font.size + line_gap
    block_height = len(lines) * line_height
    y = panel_top + 190

    accent = (scene.get("accent") or "").strip().casefold()
    for line in lines:
        line_fill = BLUE if accent and accent in line.casefold() else WHITE
        draw.text((SAFE_X + 30, y), line, font=main_font, fill=line_fill)
        y += line_height

    detail = (scene.get("detail") or "").strip()
    if detail:
        y = max(y + 60, panel_top + 190 + block_height + 65)
        detail_font = font(38, False)
        detail_lines = wrap_lines(draw, detail, detail_font, max_text_width)
        for line in detail_lines[:4]:
            draw.text((SAFE_X + 30, y), line, font=detail_font, fill=MUTED)
            y += 54

    # Bottom brand marker stays clear of platform UI safe zone.
    brand_y = HEIGHT - SAFE_BOTTOM - 40
    draw.text((SAFE_X, brand_y), "news.carni.ltd", font=font(28, False), fill=MUTED)
    counter = f"{index + 1:02d}/{len(manifest['scenes']):02d}"
    counter_box = draw.textbbox((0, 0), counter, font=font(28, True))
    draw.text((WIDTH - SAFE_X - (counter_box[2] - counter_box[0]), brand_y), counter, font=font(28, True), fill=BLUE)

    image.save(out_path, quality=95)


def build_segment(ffmpeg: str, image_path: Path, duration: float, output_path: Path) -> None:
    # Subtle deterministic zoom. Audio is silent in Stage 1; TTS replaces it later.
    zoom = "zoompan=z='min(zoom+0.00012,1.018)':d=1:s=1080x1920:fps=30,format=yuv420p"
    cmd = [
        ffmpeg,
        "-y",
        "-loop", "1",
        "-framerate", str(FPS),
        "-i", str(image_path),
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", f"{duration:.3f}",
        "-vf", zoom,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac",
        "-b:a", "96k",
        "-shortest",
        str(output_path),
    ]
    run(cmd)


def concat_segments(ffmpeg: str, segments: list[Path], output_path: Path, work_dir: Path) -> None:
    concat_file = work_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{seg.as_posix()}'\n" for seg in segments), encoding="utf-8")
    run(
        [
            ffmpeg,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_path),
        ]
    )


def validate_output(ffprobe: str, output_path: Path) -> None:
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height",
        "-of", "json",
        str(output_path),
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=True)
    info = json.loads(proc.stdout)
    streams = info.get("streams") or []
    if not streams:
        fail("Generated MP4 has no video stream")
    stream = streams[0]
    if stream.get("codec_name") != "h264" or stream.get("width") != WIDTH or stream.get("height") != HEIGHT:
        fail(f"Unexpected output video stream: {stream}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("build/shorts"))
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        fail("ffmpeg and ffprobe are required")

    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (args.output_dir / f"{manifest['id']}.mp4").resolve()

    with tempfile.TemporaryDirectory(prefix="carni-short-") as tmp:
        work_dir = Path(tmp)
        segments: list[Path] = []
        for index, scene in enumerate(manifest["scenes"]):
            image_path = work_dir / f"scene-{index:02d}.png"
            segment_path = work_dir / f"scene-{index:02d}.mp4"
            draw_scene(manifest, scene, index, image_path)
            build_segment(ffmpeg, image_path, float(scene["duration"]), segment_path)
            segments.append(segment_path)
        concat_segments(ffmpeg, segments, output_path, work_dir)

    validate_output(ffprobe, output_path)
    total = sum(float(scene["duration"]) for scene in manifest["scenes"])
    print(f"Rendered {output_path} ({total:.1f}s, {WIDTH}x{HEIGHT}, H.264/AAC)")


if __name__ == "__main__":
    main()
