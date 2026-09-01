#!/usr/bin/env python3
"""Deterministic renderer for the approved AI News by Carni Shorts storyboard.

Editorial choices live in the manifest. Rendering is purely technical:
manifest -> seven storyboard-matched HTML/CSS scenes -> PNG -> H.264/AAC MP4.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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
    fail("Google Chrome/Chromium is required")


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        lines = []
        for err in errors:
            where = ".".join(str(x) for x in err.absolute_path) or "<root>"
            lines.append(f"{where}: {err.message}")
        fail("Manifest validation failed:\n- " + "\n- ".join(lines))
    total = sum(float(s["duration"]) for s in data["scenes"])
    if not 30 <= total <= 45:
        fail(f"Storyboard duration must be 30–45 seconds, got {total:.2f}s")
    return data


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def accent_markup(text: str, accent: str | None) -> str:
    if not accent:
        return esc(text)
    low = text.casefold()
    pos = low.find(accent.casefold())
    if pos < 0:
        return esc(text)
    end = pos + len(accent)
    return f"{esc(text[:pos])}<span class=\"accent\">{esc(text[pos:end])}</span>{esc(text[end:])}"


def svg_cubes() -> str:
    cubes = []
    specs = [(330,170,150),(130,300,105),(520,330,110),(335,415,215)]
    for x,y,s in specs:
        h = s * .48
        cubes.append(f'''
        <g transform="translate({x} {y})" fill="none" stroke="#2ea7ff" stroke-width="3">
          <path d="M0 {h} L{s/2} 0 L{s} {h} L{s/2} {h*2} Z" fill="#061726"/>
          <path d="M0 {h} V{h*2.45} L{s/2} {h*3.45} V{h*2}" fill="#04111c"/>
          <path d="M{s} {h} V{h*2.45} L{s/2} {h*3.45}" fill="#082033"/>
          <path d="M0 {h*2.45} L{s/2} {h*1.45} L{s} {h*2.45}" opacity=".55"/>
        </g>''')
    return f'''
    <svg viewBox="0 0 760 760" class="art-svg">
      <defs><filter id="glow"><feGaussianBlur stdDeviation="10" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      <g opacity=".22" stroke="#2ea7ff"><path d="M40 650H720M80 80V700M170 80V700M260 80V700M350 80V700M440 80V700M530 80V700M620 80V700"/></g>
      <circle cx="440" cy="550" r="130" fill="#0b6fac" opacity=".16" filter="url(#glow)"/>
      {''.join(cubes)}
      <circle cx="440" cy="550" r="16" fill="#79d8ff" filter="url(#glow)"/>
    </svg>'''


def svg_radar() -> str:
    rings = ''.join(f'<circle cx="350" cy="350" r="{r}"/>' for r in (70,130,190,250,310))
    spokes = ''.join(f'<line x1="350" y1="350" x2="{x}" y2="{y}"/>' for x,y in ((350,30),(350,670),(30,350),(670,350),(124,124),(576,124),(124,576),(576,576)))
    dots = ''.join(f'<circle cx="{x}" cy="{y}" r="6" fill="#2ea7ff"/>' for x,y in ((350,40),(350,160),(480,350),(210,350),(490,210),(215,500),(585,500)))
    return f'''
    <svg viewBox="0 0 700 700" class="art-svg radar-svg">
      <defs><radialGradient id="rg"><stop stop-color="#2ea7ff" stop-opacity=".33"/><stop offset="1" stop-color="#2ea7ff" stop-opacity="0"/></radialGradient></defs>
      <circle cx="350" cy="350" r="345" fill="url(#rg)" opacity=".4"/>
      <g fill="none" stroke="#2ea7ff" stroke-width="2" opacity=".72">{rings}{spokes}</g>
      {dots}<circle cx="350" cy="350" r="18" fill="#b9ebff"/><circle cx="350" cy="350" r="48" fill="none" stroke="#2ea7ff" stroke-width="3"/>
    </svg>'''


def svg_agents() -> str:
    return '''
    <svg viewBox="0 0 900 620" class="art-svg">
      <g opacity=".22" stroke="#2ea7ff" fill="none"><path d="M40 90H860M40 180H860M40 270H860M40 360H860M40 450H860"/><path d="M180 40V560M450 40V560M720 40V560"/></g>
      <g transform="translate(70 245)">
        <circle cx="110" cy="110" r="105" fill="#051b2b" stroke="#1b6e9f" stroke-width="3"/>
        <path d="M55 145h26v-45H55zm48 0h26V75h-26zm48 0h26V45h-26" fill="none" stroke="#2ea7ff" stroke-width="7"/><path d="M50 70l62-38 48 18 44-36" fill="none" stroke="#8ad5ff" stroke-width="6"/>
        <text x="110" y="255" text-anchor="middle" fill="#f1f7fb" font-size="29" font-family="Inter,DejaVu Sans">ФИНАНСЫ</text>
      </g>
      <g transform="translate(345 245)">
        <circle cx="110" cy="110" r="105" fill="#051b2b" stroke="#1b6e9f" stroke-width="3"/>
        <path d="M42 88h100v70H42zM142 110h45l35 30v18h-80z" fill="none" stroke="#2ea7ff" stroke-width="7"/><circle cx="78" cy="165" r="15" fill="#8ad5ff"/><circle cx="176" cy="165" r="15" fill="#8ad5ff"/>
        <text x="110" y="255" text-anchor="middle" fill="#f1f7fb" font-size="29" font-family="Inter,DejaVu Sans">ЛОГИСТИКА</text>
      </g>
      <g transform="translate(620 245)">
        <circle cx="110" cy="110" r="105" fill="#051b2b" stroke="#1b6e9f" stroke-width="3"/>
        <path d="M45 65h132a25 25 0 0 1 25 25v55a25 25 0 0 1-25 25h-48l-36 35 7-35H70a25 25 0 0 1-25-25V90a25 25 0 0 1 25-25z" fill="none" stroke="#2ea7ff" stroke-width="7"/><circle cx="90" cy="118" r="7" fill="#8ad5ff"/><circle cx="123" cy="118" r="7" fill="#8ad5ff"/><circle cx="156" cy="118" r="7" fill="#8ad5ff"/>
        <text x="110" y="255" text-anchor="middle" fill="#f1f7fb" font-size="25" font-family="Inter,DejaVu Sans">ПОДДЕРЖКА</text><text x="110" y="286" text-anchor="middle" fill="#f1f7fb" font-size="25" font-family="Inter,DejaVu Sans">КЛИЕНТОВ</text>
      </g>
      <circle cx="820" cy="90" r="8" fill="#2ea7ff"/><circle cx="790" cy="130" r="4" fill="#8ad5ff"/><path d="M820 90l-30 40-55 30" stroke="#2ea7ff" opacity=".55"/>
    </svg>'''


def svg_growth() -> str:
    bars = ''.join(f'<rect x="{90+i*70}" y="{470-h}" width="42" height="{h}" rx="4" fill="#083052" stroke="#177db8"/>' for i,h in enumerate((55,80,120,155,210,280,350,430,520)))
    return f'''
    <svg viewBox="0 0 780 650" class="art-svg">
      <defs><filter id="glow2"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      <g opacity=".18" stroke="#2ea7ff"><path d="M70 520H740M70 420H740M70 320H740M70 220H740M70 120H740"/></g>
      {bars}
      <path d="M80 505 C170 500 205 465 275 450 S385 405 445 350 S560 295 620 220 S690 145 720 65" fill="none" stroke="#3db8ff" stroke-width="7" filter="url(#glow2)"/>
      <g fill="#b9ebff">{''.join(f'<circle cx="{x}" cy="{y}" r="8"/>' for x,y in ((80,505),(205,465),(385,405),(560,295),(690,145),(720,65)))}</g>
      <path d="M700 82l22-18 4 28" fill="#8ad5ff"/>
    </svg>'''


def svg_globe() -> str:
    return '''
    <svg viewBox="0 0 720 720" class="art-svg globe-svg">
      <defs><radialGradient id="earth"><stop stop-color="#0b91db" stop-opacity=".75"/><stop offset=".72" stop-color="#063b66" stop-opacity=".55"/><stop offset="1" stop-color="#020a12" stop-opacity=".3"/></radialGradient><filter id="glo"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      <circle cx="360" cy="360" r="305" fill="url(#earth)" stroke="#2ea7ff" stroke-width="3" filter="url(#glo)"/>
      <g fill="none" stroke="#6fd1ff" stroke-width="2" opacity=".48"><ellipse cx="360" cy="360" rx="305" ry="105"/><ellipse cx="360" cy="360" rx="305" ry="205"/><ellipse cx="360" cy="360" rx="125" ry="305"/><ellipse cx="360" cy="360" rx="225" ry="305"/></g>
      <path d="M205 185l55 12 32 48 54 10 35 42-18 52-55 18-25 58-59-16-35-61-49-23 10-75zM420 250l58-38 78 27 31 47-24 45-61 10-25 50-52-20-30-53zM410 455l62-26 60 35-18 73-76 37-55-41z" fill="#2ea7ff" opacity=".45"/>
    </svg>'''


def card_shell(inner: str, extra_class: str) -> str:
    return f'<main class="story-card {extra_class}"><div class="circuit"></div>{inner}</main>'


def scene_html(manifest: dict, scene: dict, index: int, css: str) -> str:
    visual = scene["visual"]
    text = accent_markup(scene["text"], scene.get("accent"))
    detail = esc(scene.get("detail") or "")

    if visual == "story-hook":
        inner = f'<section class="hook-center"><h1>{text}</h1></section>'
    elif visual == "erp-cubes":
        inner = f'<section class="split scene-copy"><h1>{text}</h1><p>{detail}</p></section><section class="split scene-art">{svg_cubes()}</section>'
    elif visual == "decision-radar":
        inner = f'<section class="split scene-copy decision-copy"><h1>{text}</h1></section><section class="split scene-art radar-art">{svg_radar()}</section>'
    elif visual == "agents-processes":
        inner = f'<section class="agents-title"><h1>{text}</h1></section><section class="agents-art">{svg_agents()}</section>'
    elif visual == "infra-growth":
        inner = f'<section class="growth-copy"><h1>{text}</h1></section><section class="growth-art">{svg_growth()}</section>'
    elif visual == "cta-globe":
        inner = f'''<section class="cta-copy"><h1>{text}</h1><p>{detail}</p>
          <div class="cta-pill">➤ <span>Telegram:</span> t.me/+KotqtD1F8EEwZDli</div>
          <div class="cta-pill">◎ <span>Сайт:</span> news.carni.ltd</div>
        </section><section class="cta-art">{svg_globe()}</section>'''
    elif visual == "outro-brand":
        inner = f'''<section class="outro-center"><div class="outro-ai">AI NEWS</div><div class="outro-by">BY CARNI</div><div class="outro-tagline">{detail}</div></section>'''
    else:
        fail(f"Unsupported visual: {visual}")

    return f'''<!doctype html><html lang="{esc(manifest['lang'])}"><head><meta charset="utf-8"><style>{css}</style></head>
    <body><div class="canvas">{card_shell(inner, 'visual-' + visual)}</div></body></html>'''


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
            page.wait_for_timeout(100)
            image_path = work_dir / f"scene-{index:02d}.png"
            page.screenshot(path=str(image_path), full_page=False)
            images.append(image_path)
        browser.close()
    return images


def build_segment(ffmpeg: str, image_path: Path, duration: float, output_path: Path, index: int) -> None:
    # restrained movement: same storyboard frame, gentle camera drift only
    if index in (0, 6):
        zoom = "zoompan=z='min(zoom+0.00013,1.016)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
    elif index % 2:
        zoom = "zoompan=z='min(zoom+0.00008,1.012)':x='iw/2-(iw/zoom/2)-6':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
    else:
        zoom = "zoompan=z='min(zoom+0.00008,1.012)':x='iw/2-(iw/zoom/2)+6':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
    run([
        ffmpeg, "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(image_path),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", f"{duration:.3f}", "-vf", f"{zoom},format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS),
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
    print(f"Rendered {output_path} ({total:.1f}s, {WIDTH}x{HEIGHT}, H.264/AAC, storyboard matched)")


if __name__ == "__main__":
    main()
