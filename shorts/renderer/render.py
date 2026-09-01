#!/usr/bin/env python3
"""Carni Shorts v1.1 deterministic renderer.

Editorial intelligence lives in the manifest. This renderer is a visual/technical
layer only: validated manifest -> branded HTML/CSS scenes -> PNG -> H.264/AAC MP4.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import qrcode
from jsonschema import Draft202012Validator, FormatChecker
from playwright.sync_api import sync_playwright

WIDTH = 1080
HEIGHT = 1920
FPS = 30
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "shorts" / "schema" / "manifest.schema.json"
STYLE_PATH = ROOT / "shorts" / "renderer" / "style.css"


def fail(message: str) -> None:
    raise SystemExit(message)


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        fail(f"Command failed: {' '.join(cmd)}")


def find_chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    fail("Google Chrome/Chromium is required for HTML/CSS rendering")


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


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def accent_markup(text: str, accent: str | None) -> str:
    if not accent:
        return esc(text)
    pos = text.casefold().find(accent.casefold())
    if pos < 0:
        return esc(text)
    end = pos + len(accent)
    return f"{esc(text[:pos])}<span class=\"accent\">{esc(text[pos:end])}</span>{esc(text[end:])}"


def qr_data_uri(url: str) -> str:
    qr = qrcode.QRCode(version=None, box_size=8, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#082033", back_color="white").convert("RGB")
    out = io.BytesIO()
    image.save(out, format="PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")


def svg_hero() -> str:
    return """
    <svg viewBox="0 0 900 620" role="img" aria-label="Технологическая архитектура">
      <defs>
        <linearGradient id="g" x1="0" x2="1"><stop stop-color="#157fc5"/><stop offset="1" stop-color="#42bdff"/></linearGradient>
        <filter id="glow"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <g opacity=".22" stroke="#2ea7ff" fill="none">
        <circle cx="610" cy="305" r="215"/><circle cx="610" cy="305" r="155"/><circle cx="610" cy="305" r="95"/>
        <path d="M60 480H270V420H390M80 150H250V220H365"/>
      </g>
      <g transform="translate(355 92)" stroke="url(#g)" stroke-width="4" fill="#061a29" filter="url(#glow)">
        <path d="M250 0 470 110 250 220 30 110Z"/>
        <path d="M30 110v255l220 115 220-115V110"/>
        <path d="M250 220v260M30 110l220 110 220-110"/>
        <path d="M95 145l155 78 155-78v166l-155 82-155-82Z" opacity=".72"/>
      </g>
      <g fill="#2ea7ff">
        <circle cx="104" cy="482" r="7"/><circle cx="270" cy="420" r="7"/><circle cx="82" cy="150" r="7"/><circle cx="250" cy="220" r="7"/>
      </g>
      <text x="62" y="555" fill="#8ad5ff" font-size="28" font-family="Inter,DejaVu Sans">МОДЕЛИ  ·  АГЕНТЫ  ·  ДАННЫЕ  ·  ИНФРАСТРУКТУРА</text>
    </svg>"""


def svg_network(items: list[str]) -> str:
    labels = (items + ["Сеть", "Контейнеры", "Изоляция", "Доступ"])[:4]
    coords = [(160, 160), (590, 125), (690, 465), (190, 500)]
    nodes = []
    for (x, y), label in zip(coords, labels):
        nodes.append(f'<g><circle cx="{x}" cy="{y}" r="62" fill="#071d2c" stroke="#2ea7ff" stroke-width="3"/><text x="{x}" y="{y+9}" text-anchor="middle" fill="#dff5ff" font-size="24" font-family="Inter,DejaVu Sans">{esc(label)}</text></g>')
    return f"""
    <svg viewBox="0 0 850 650">
      <g stroke="#2ea7ff" stroke-width="3" opacity=".42"><path d="M210 190 382 285M545 170 455 280M625 430 470 355M235 450 385 360"/></g>
      <circle cx="425" cy="320" r="128" fill="#061a29" stroke="#52c4ff" stroke-width="4"/>
      <path d="M425 222l72 28v62c0 67-42 113-72 132-30-19-72-65-72-132v-62Z" fill="#0b2a40" stroke="#2ea7ff" stroke-width="5"/>
      <path d="M389 319l26 27 50-61" fill="none" stroke="#8ad5ff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
      {''.join(nodes)}
      <circle cx="425" cy="320" r="173" fill="none" stroke="#2ea7ff" opacity=".18" stroke-width="2"/>
    </svg>"""


def svg_attack_chain(items: list[str]) -> str:
    labels = (items + ["GPU-кластер", "Сеть", "Контейнер", "Приложение"])[:4]
    xs = [120, 335, 550, 765]
    boxes = []
    arrows = []
    for i, (x, label) in enumerate(zip(xs, labels)):
        boxes.append(f'<g><rect x="{x-82}" y="250" width="164" height="120" rx="24" fill="#071d2c" stroke="#2ea7ff" stroke-width="3"/><text x="{x}" y="320" text-anchor="middle" fill="#eef8fd" font-size="24" font-family="Inter,DejaVu Sans">{esc(label)}</text><circle cx="{x}" cy="215" r="14" fill="#2ea7ff"/></g>')
        if i < 3:
            arrows.append(f'<path d="M{x+86} 310H{xs[i+1]-95}" stroke="#8ad5ff" stroke-width="4"/><path d="M{xs[i+1]-108} 296l18 14-18 14" fill="none" stroke="#8ad5ff" stroke-width="4"/>')
    return f"""
    <svg viewBox="0 0 900 580">
      <defs><linearGradient id="risk" x1="0" x2="1"><stop stop-color="#2ea7ff"/><stop offset="1" stop-color="#ff6b7d"/></linearGradient></defs>
      <path d="M75 465C220 405 298 493 425 430S670 370 825 430" fill="none" stroke="url(#risk)" stroke-width="5" opacity=".72"/>
      {''.join(arrows)}{''.join(boxes)}
      <g transform="translate(680 65)"><circle cx="70" cy="70" r="64" fill="#2b121a" stroke="#ff6b7d" stroke-width="4"/><path d="M38 38l64 64M102 38 38 102" stroke="#ff91a0" stroke-width="9" stroke-linecap="round"/></g>
      <text x="70" y="530" fill="#9eb6c5" font-size="25" font-family="Inter,DejaVu Sans">РИСК ДВИЖЕТСЯ ПО ЦЕПОЧКЕ ВМЕСТЕ С ДОСТУПОМ</text>
    </svg>"""


def svg_provider(items: list[str]) -> str:
    labels = (items + ["Модели", "Агенты", "Приложения"])[:3]
    top = []
    xs = [160, 425, 690]
    for x, label in zip(xs, labels):
        top.append(f'<g><circle cx="{x}" cy="155" r="72" fill="#071d2c" stroke="#2ea7ff" stroke-width="3"/><circle cx="{x}" cy="155" r="38" fill="#0d3450"/><text x="{x}" y="265" text-anchor="middle" fill="#dff5ff" font-size="26" font-family="Inter,DejaVu Sans">{esc(label)}</text><path d="M{x} 228V330" stroke="#2ea7ff" stroke-width="3" opacity=".65"/></g>')
    return f"""
    <svg viewBox="0 0 850 720">
      {''.join(top)}
      <g transform="translate(120 335)">
        <rect x="0" y="0" width="610" height="245" rx="28" fill="#061a29" stroke="#2ea7ff" stroke-width="3"/>
        <g fill="#0a2a40" stroke="#43baff" stroke-width="2">
          <rect x="50" y="45" width="150" height="58" rx="10"/><rect x="230" y="45" width="150" height="58" rx="10"/><rect x="410" y="45" width="150" height="58" rx="10"/>
          <rect x="50" y="135" width="150" height="58" rx="10"/><rect x="230" y="135" width="150" height="58" rx="10"/><rect x="410" y="135" width="150" height="58" rx="10"/>
        </g>
        <g fill="#2ea7ff"><circle cx="78" cy="74" r="7"/><circle cx="258" cy="74" r="7"/><circle cx="438" cy="74" r="7"/><circle cx="78" cy="164" r="7"/><circle cx="258" cy="164" r="7"/><circle cx="438" cy="164" r="7"/></g>
      </g>
      <text x="425" y="660" text-anchor="middle" fill="#8ad5ff" font-size="25" font-family="Inter,DejaVu Sans">ОДИН ВЫЧИСЛИТЕЛЬНЫЙ СЛОЙ — МНОГО РЕАЛЬНЫХ ДЕЙСТВИЙ</text>
    </svg>"""


def svg_check(items: list[str]) -> str:
    labels = (items + ["Изоляция", "Патчи", "Сеть", "Секреты", "Доступ"])[:5]
    rows = []
    for i, label in enumerate(labels):
        y = 110 + i * 72
        rows.append(f'<g><circle cx="90" cy="{y}" r="20" fill="#0e3852" stroke="#2ea7ff" stroke-width="2"/><path d="M80 {y}l8 8 15-18" fill="none" stroke="#8ad5ff" stroke-width="4" stroke-linecap="round"/><text x="130" y="{y+9}" fill="#e8f6fd" font-size="29" font-family="Inter,DejaVu Sans">{esc(label)}</text></g>')
    return f"""
    <svg viewBox="0 0 900 520">
      <rect x="40" y="40" width="390" height="420" rx="28" fill="#061a29" stroke="#2ea7ff" stroke-width="3"/>
      {''.join(rows)}
      <g transform="translate(485 70)">
        <path d="M0 340H340M0 340V20" stroke="#37657e" stroke-width="3"/>
        <path d="M20 300 95 250 160 268 225 165 305 75" fill="none" stroke="#2ea7ff" stroke-width="7" stroke-linecap="round"/>
        <path d="M292 78l18-11-3 21" fill="#8ad5ff"/>
        <g fill="#8ad5ff"><circle cx="20" cy="300" r="8"/><circle cx="95" cy="250" r="8"/><circle cx="160" cy="268" r="8"/><circle cx="225" cy="165" r="8"/><circle cx="305" cy="75" r="8"/></g>
        <text x="170" y="405" text-anchor="middle" fill="#9eb6c5" font-size="24" font-family="Inter,DejaVu Sans">ТРЕБОВАНИЯ К ПРОВАЙДЕРУ РАСТУТ</text>
      </g>
    </svg>"""


def scene_visual(scene: dict) -> str:
    visual = scene.get("visual") or "hero-grid"
    items = list(scene.get("visual_items") or [])
    if visual == "risk-network":
        return svg_network(items)
    if visual == "attack-chain":
        return svg_attack_chain(items)
    if visual == "provider-stack":
        return svg_provider(items)
    if visual == "security-check":
        return svg_check(items)
    return svg_hero()


def topbar(index: int, count: int, manifest: dict) -> str:
    progress = round(100 * (index + 1) / count, 2)
    label = f"{'RU' if manifest['lang'] == 'ru' else 'EN'} · {manifest['kind'].upper()}"
    return f"""
      <header class="topbar">
        <div class="brand"><span class="brand-ai">AI NEWS</span><span class="brand-by">BY CARNI</span></div>
        <div class="issue">{esc(label)}</div>
        <div class="progress" style="width:{progress}%"></div>
      </header>"""


def footer(index: int, count: int) -> str:
    return f'<footer class="footer"><span>news.carni.ltd</span><span class="counter">{index+1:02d}/{count:02d}</span></footer>'


def scene_html(manifest: dict, scene: dict, index: int, css: str) -> str:
    count = len(manifest["scenes"])
    kicker = esc(scene.get("kicker") or scene["type"])
    headline = accent_markup(scene["text"], scene.get("accent"))
    detail = esc(scene.get("detail") or "")
    visual = scene.get("visual") or "hero-grid"
    chips = "".join(f'<span class="chip">{esc(item)}</span>' for item in scene.get("visual_items") or [])

    if scene["type"] == "cta":
        site = manifest["report_url"]
        telegram = manifest["telegram_url"]
        body = f"""
          <main class="stage">
            <div class="cta-heading">
              <div class="kicker">{kicker}</div>
              <h1 class="headline">{headline}</h1>
              <div class="detail" style="margin-left:auto;margin-right:auto">{detail}</div>
            </div>
            <div class="cta-grid">
              <section class="panel link-card">
                <div class="link-icon">↗</div><div class="link-title">Сайт</div>
                <div class="link-url">news.carni.ltd</div>
                <div class="qr-wrap"><img src="{qr_data_uri(site)}"></div>
                <div class="cta-note">Полный аналитический выпуск</div>
              </section>
              <section class="panel link-card">
                <div class="link-icon">➤</div><div class="link-title">Telegram</div>
                <div class="link-url">t.me/+KotqtD1F8EEwZDli</div>
                <div class="qr-wrap"><img src="{qr_data_uri(telegram)}"></div>
                <div class="cta-note">AI News by Carni (RU)</div>
              </section>
            </div>
          </main>"""
        scene_class = "scene-cta"
    elif visual == "hero-grid":
        body = f"""
          <main class="stage">
            <section class="hero-copy"><div class="kicker">{kicker}</div><h1 class="headline big">{headline}</h1><div class="detail">{detail}</div></section>
            <section class="panel hero-art">{scene_visual(scene)}</section>
          </main>"""
        scene_class = "scene-hook"
    elif visual in {"risk-network", "provider-stack"}:
        metric = esc(scene.get("metric") or "")
        metric_label = esc(scene.get("metric_label") or "")
        metric_html = f'<div class="metric">{metric}</div><div class="metric-small">{metric_label}</div>' if metric else ""
        body = f"""
          <main class="stage">
            <section class="panel copy-panel"><div class="kicker">{kicker}</div>{metric_html}<h1 class="headline">{headline}</h1><div class="detail">{detail}</div><div class="chip-row">{chips}</div></section>
            <section class="panel visual-panel">{scene_visual(scene)}</section>
          </main>"""
        scene_class = f"scene-{visual}"
    elif visual == "attack-chain":
        body = f"""
          <main class="stage">
            <section class="panel copy-wide"><div class="kicker">{kicker}</div><h1 class="headline">{headline}</h1><div class="detail">{detail}</div></section>
            <section class="panel diagram-wide">{scene_visual(scene)}</section>
          </main>"""
        scene_class = "scene-attack-chain"
    else:
        body = f"""
          <main class="stage">
            <section class="panel check-visual">{scene_visual(scene)}</section>
            <section class="panel takeaway-copy"><div class="kicker">{kicker}</div><h1 class="headline">{headline}</h1><div class="detail">{detail}</div><div class="chip-row">{chips}</div></section>
          </main>"""
        scene_class = "scene-security-check"

    return f"""<!doctype html><html lang="{esc(manifest['lang'])}"><head><meta charset="utf-8"><style>{css}</style></head>
    <body><div class="canvas {scene_class}"><div class="grid"></div><div class="glow"></div>{topbar(index,count,manifest)}{body}{footer(index,count)}</div></body></html>"""


def screenshot_scenes(manifest: dict, work_dir: Path) -> list[Path]:
    css = STYLE_PATH.read_text(encoding="utf-8")
    chrome = find_chrome()
    images: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
        for index, scene in enumerate(manifest["scenes"]):
            page.set_content(scene_html(manifest, scene, index, css), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(120)
            image_path = work_dir / f"scene-{index:02d}.png"
            page.screenshot(path=str(image_path), full_page=False)
            images.append(image_path)
        browser.close()
    return images


def build_segment(ffmpeg: str, image_path: Path, duration: float, output_path: Path, index: int) -> None:
    direction = 1 if index % 2 == 0 else -1
    if direction > 0:
        zoom = "zoompan=z='min(zoom+0.00010,1.014)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
    else:
        zoom = "zoompan=z='if(eq(on,1),1.014,max(zoom-0.00010,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
    vf = f"{zoom},format=yuv420p"
    run([
        ffmpeg, "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(image_path),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", f"{duration:.3f}", "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "96k", "-shortest", str(output_path)
    ])


def concat_segments(ffmpeg: str, segments: list[Path], output_path: Path, work_dir: Path) -> None:
    concat_file = work_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{seg.as_posix()}'\n" for seg in segments), encoding="utf-8")
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", str(output_path)])


def validate_output(ffprobe: str, output_path: Path) -> None:
    proc = subprocess.run([
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate", "-of", "json", str(output_path)
    ], text=True, capture_output=True, check=True)
    streams = json.loads(proc.stdout).get("streams") or []
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

    manifest = load_manifest(args.manifest.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (args.output_dir / f"{manifest['id']}.mp4").resolve()

    with tempfile.TemporaryDirectory(prefix="carni-short-") as tmp:
        work_dir = Path(tmp)
        images = screenshot_scenes(manifest, work_dir)
        segments: list[Path] = []
        for index, (scene, image_path) in enumerate(zip(manifest["scenes"], images)):
            segment_path = work_dir / f"scene-{index:02d}.mp4"
            build_segment(ffmpeg, image_path, float(scene["duration"]), segment_path, index)
            segments.append(segment_path)
        concat_segments(ffmpeg, segments, output_path, work_dir)

    validate_output(ffprobe, output_path)
    total = sum(float(scene["duration"]) for scene in manifest["scenes"])
    print(f"Rendered {output_path} ({total:.1f}s, {WIDTH}x{HEIGHT}, H.264/AAC, Carni v1.1)")


if __name__ == "__main__":
    main()
