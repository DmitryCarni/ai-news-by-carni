#!/usr/bin/env python3
"""Storyboard-faithful renderer for AI News by Carni Shorts.

The attached/user-approved storyboard is the visual specification.
This module does not invent a new design; it deterministically maps a manifest
to seven storyboard-matched HTML/CSS/SVG scenes, then to 1080x1920 MP4.
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

    total = sum(float(scene["duration"]) for scene in data["scenes"])
    if not 30 <= total <= 45:
        fail(f"Storyboard duration must be 30–45 seconds, got {total:.2f}s")
    if len(data["scenes"]) != 7:
        fail(f"Approved storyboard requires exactly 7 scenes, got {len(data['scenes'])}")
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
    return f'{esc(text[:pos])}<span class="accent">{esc(text[pos:end])}</span>{esc(text[end:])}'


def lines_html(lines: list[tuple[str, bool]]) -> str:
    return "".join(
        f'<span class="title-line{" accent" if accent else ""}">{esc(text)}</span>'
        for text, accent in lines
    )


def storyboard_lines(scene: dict) -> str:
    visual = scene["visual"]
    if visual == "story-hook":
        return lines_html([("ИИ НАКОНЕЦ", False), ("ВЫХОДИТ", False), ("ИЗ ДЕМО", True)])
    if visual == "erp-cubes":
        return lines_html([("ERP", False), ("НАЧИНАЮТ", False), ("ПРОЕКТИРОВАТЬ", False), ("С ИИ С НУЛЯ", True)])
    if visual == "decision-radar":
        return lines_html([
            ("РЫНКУ НУЖНЫ", False), ("НЕ ЧАТ-БОТЫ,", False), ("А СИСТЕМЫ,", False),
            ("КОТОРЫЕ", False), ("ПРИНИМАЮТ", True), ("РЕШЕНИЯ", True),
        ])
    if visual == "agents-processes":
        return lines_html([("ИИ-АГЕНТЫ УЖЕ", False), ("РАБОТАЮТ В РЕАЛЬНЫХ", True), ("ПРОЦЕССАХ", True)])
    if visual == "infra-growth":
        return lines_html([("ИИ ПЕРЕХОДИТ", False), ("ОТ ЭКСПЕРИМЕНТОВ", False), ("К ИНФРАСТРУКТУРЕ", True)])
    if visual == "cta-globe":
        return lines_html([("ПОЛНЫЙ РАЗБОР —", False), ("AI NEWS BY CARNI", True)])
    return accent_markup(scene["text"], scene.get("accent"))


def circuit_svg(mode: str) -> str:
    left_paths = [
        "M30 160H185V215H250", "M30 230H130V300H230", "M45 385H170V345H260",
        "M35 520H145V600H245", "M42 690H210V650H280", "M28 845H150V790H255",
        "M40 1010H185V1080H270", "M28 1165H135V1230H245", "M44 1360H205V1315H275",
        "M30 1515H150V1595H245",
    ]
    right_paths = [
        "M1050 145H885V205H810", "M1048 275H925V335H825", "M1038 430H875V385H800",
        "M1050 590H930V655H825", "M1035 770H890V720H795", "M1052 920H925V990H820",
        "M1038 1110H885V1060H800", "M1050 1260H930V1325H830", "M1035 1440H885V1390H800",
        "M1048 1600H920V1660H825",
    ]
    opacity = ".34" if mode in {"erp-cubes", "decision-radar"} else ".28" if mode in {"agents-processes", "infra-growth"} else ".42"
    paths = "".join(f'<path d="{p}"/>' for p in left_paths + right_paths)
    nodes = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}"/>'
        for x, y, r in [
            (185,215,4),(130,300,3),(170,345,4),(145,600,3),(210,650,4),
            (885,205,4),(925,335,3),(875,385,4),(930,655,3),(890,720,4),
            (185,1080,4),(135,1230,3),(205,1315,4),(885,1060,4),(930,1325,3),
        ]
    )
    hud = ""
    if mode in {"story-hook", "outro-brand"}:
        hud = '''
          <g transform="translate(815 650)" opacity=".7">
            <rect width="170" height="92" rx="10"/>
            <path d="M20 22H92M20 42H142M20 62H74M118 22v45M132 22v45"/>
            <circle cx="104" cy="62" r="5"/><circle cx="148" cy="22" r="5"/>
          </g>'''
    return f'''
    <svg class="circuit-art" viewBox="0 0 1080 1920" aria-hidden="true">
      <g fill="none" stroke="#1f8fd0" stroke-width="2" opacity="{opacity}">
        {paths}{hud}
      </g>
      <g fill="#2ea7ff" opacity=".72">{nodes}</g>
      <g stroke="#0d5179" stroke-width="1" opacity=".23">
        <path d="M110 95H970"/><path d="M110 1820H970"/>
        <path d="M150 120V1800"/><path d="M930 120V1800"/>
      </g>
    </svg>'''


def iso_box(cx: float, cy: float, w: float, d: float, h: float, strong: bool = False) -> str:
    x1, y1 = cx, cy - d / 2
    x2, y2 = cx + w / 2, cy
    x3, y3 = cx, cy + d / 2
    x4, y4 = cx - w / 2, cy
    top = f"{x1},{y1} {x2},{y2} {x3},{y3} {x4},{y4}"
    left = f"{x4},{y4} {x3},{y3} {x3},{y3+h} {x4},{y4+h}"
    right = f"{x2},{y2} {x3},{y3} {x3},{y3+h} {x2},{y2+h}"
    stroke = "#65ceff" if strong else "#219ce4"
    return f'''
      <g stroke="{stroke}" stroke-width="2.6">
        <polygon points="{top}" fill="#08243a" fill-opacity=".78"/>
        <polygon points="{left}" fill="#03131f" fill-opacity=".96"/>
        <polygon points="{right}" fill="#062037" fill-opacity=".92"/>
      </g>'''


def svg_cubes() -> str:
    boxes = [
        iso_box(400, 400, 390, 160, 92, True),
        iso_box(400, 505, 390, 160, 78, True),
        iso_box(400, 598, 390, 160, 68, False),
        iso_box(235, 310, 118, 58, 100, False),
        iso_box(565, 315, 118, 58, 100, False),
        iso_box(400, 185, 180, 84, 150, True),
        iso_box(400, 342, 145, 70, 115, True),
    ]
    return f'''
    <svg viewBox="0 0 800 800" class="art-svg erp-stack" aria-hidden="true">
      <defs>
        <filter id="erpGlow"><feGaussianBlur stdDeviation="9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <radialGradient id="erpCore"><stop stop-color="#99e8ff"/><stop offset=".22" stop-color="#26b4ff" stop-opacity=".95"/><stop offset="1" stop-color="#158bd1" stop-opacity="0"/></radialGradient>
      </defs>
      <g fill="none" stroke="#125b88" stroke-width="1.4" opacity=".42">
        <path d="M70 95H730M70 705H730M95 70V730M705 70V730"/>
        <path d="M115 120l110 0 0 46 78 0M685 145l-105 0 0 55-72 0"/>
        <path d="M70 160H250M75 665H270M530 115H710M565 665H725"/>
      </g>
      <g opacity=".95">{''.join(boxes)}</g>
      <circle cx="400" cy="455" r="120" fill="url(#erpCore)" opacity=".52" filter="url(#erpGlow)"/>
      <circle cx="400" cy="455" r="10" fill="#bcefff" filter="url(#erpGlow)"/>
      <g fill="#2ea7ff">
        <circle cx="110" cy="120" r="5"/><circle cx="224" cy="120" r="4"/><circle cx="685" cy="145" r="5"/>
        <circle cx="95" cy="665" r="4"/><circle cx="705" cy="665" r="4"/>
      </g>
    </svg>'''


def svg_radar() -> str:
    rings = "".join(f'<circle cx="360" cy="360" r="{r}"/>' for r in (68,126,184,242,300))
    spokes = "".join(
        f'<line x1="360" y1="360" x2="{x}" y2="{y}"/>'
        for x,y in ((360,38),(360,682),(38,360),(682,360),(132,132),(588,132),(132,588),(588,588))
    )
    dots = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="#2ea7ff"/>'
        for x,y,r in ((360,60,6),(360,182,4),(493,360,6),(224,360,4),(495,215,5),(220,505,5),(590,505,4),(298,292,4))
    )
    return f'''
    <svg viewBox="0 0 720 720" class="art-svg radar-svg" aria-hidden="true">
      <defs><radialGradient id="radarGlow"><stop stop-color="#2ea7ff" stop-opacity=".32"/><stop offset=".52" stop-color="#0e68a2" stop-opacity=".08"/><stop offset="1" stop-opacity="0"/></radialGradient></defs>
      <rect x="20" y="20" width="680" height="680" fill="#020a11" fill-opacity=".18" stroke="#0a4770" stroke-width="1.5"/>
      <circle cx="360" cy="360" r="338" fill="url(#radarGlow)"/>
      <g fill="none" stroke="#229adf" stroke-width="2" opacity=".76">{rings}{spokes}</g>
      <g fill="none" stroke="#0b5f8f" stroke-width="1.3" opacity=".6">
        <path d="M35 110H120V70H180M685 115H600V75H545M35 610H125V655H190M685 610H595V655H535"/>
      </g>
      {dots}
      <circle cx="360" cy="360" r="18" fill="#c4f1ff"/>
      <circle cx="360" cy="360" r="48" fill="none" stroke="#2ea7ff" stroke-width="3"/>
      <circle cx="360" cy="360" r="86" fill="none" stroke="#2ea7ff" stroke-width="1.3" opacity=".3"/>
    </svg>'''


def icon_finance() -> str:
    return '''<svg viewBox="0 0 180 180"><path d="M38 130h22V91H38zm39 0h22V67H77zm39 0h22V42h-22" fill="none" stroke="#2ea7ff" stroke-width="7"/><path d="M32 75l45-33 34 14 39-31" fill="none" stroke="#8ad5ff" stroke-width="6"/><path d="M136 25h16v16" fill="none" stroke="#8ad5ff" stroke-width="5"/></svg>'''


def icon_logistics() -> str:
    return '''<svg viewBox="0 0 180 180"><path d="M25 65h92v62H25zM117 82h26l27 26v19h-53z" fill="none" stroke="#2ea7ff" stroke-width="7"/><circle cx="54" cy="137" r="13" fill="#8ad5ff"/><circle cx="137" cy="137" r="13" fill="#8ad5ff"/></svg>'''


def icon_support() -> str:
    return '''<svg viewBox="0 0 180 180"><path d="M26 54h128a22 22 0 0 1 22 22v47a22 22 0 0 1-22 22h-46l-34 29 7-29H48a22 22 0 0 1-22-22V76a22 22 0 0 1 22-22z" fill="none" stroke="#2ea7ff" stroke-width="7"/><circle cx="72" cy="99" r="6" fill="#8ad5ff"/><circle cx="101" cy="99" r="6" fill="#8ad5ff"/><circle cx="130" cy="99" r="6" fill="#8ad5ff"/></svg>'''


def svg_agents_bg() -> str:
    return '''
    <svg viewBox="0 0 1080 760" class="agents-bg" aria-hidden="true">
      <g fill="none" stroke="#0e5f8f" stroke-width="1.4" opacity=".45">
        <path d="M580 60H890V130H1010M620 155H790V220H965M680 270H900V330H1030"/>
        <path d="M615 430H820V500H990M690 550H860V620H1030"/>
      </g>
      <g fill="#2ea7ff" opacity=".75">
        <circle cx="890" cy="130" r="5"/><circle cx="790" cy="220" r="4"/><circle cx="900" cy="330" r="5"/><circle cx="820" cy="500" r="5"/><circle cx="860" cy="620" r="4"/>
      </g>
      <circle cx="930" cy="270" r="85" fill="#0a6da5" opacity=".08"/>
      <circle cx="930" cy="270" r="10" fill="#64d1ff" opacity=".8"/>
      <g stroke="#2ea7ff" opacity=".36">
        <path d="M930 270l-95-110M930 270l85-80M930 270l-125 65M930 270l74 120"/>
      </g>
    </svg>'''


def svg_growth() -> str:
    heights = (55,80,120,155,210,280,350,430,520)
    bars = "".join(
        f'<rect x="{85+i*72}" y="{505-h}" width="44" height="{h}" rx="3" fill="#07243b" stroke="#167bb5" stroke-width="1.8"/>'
        for i,h in enumerate(heights)
    )
    return f'''
    <svg viewBox="0 0 800 650" class="art-svg growth-svg" aria-hidden="true">
      <defs><filter id="growthGlow"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      <g fill="none" stroke="#0b527b" stroke-width="1.2" opacity=".45">
        <path d="M60 540H760M60 450H760M60 360H760M60 270H760M60 180H760M60 90H760"/>
        <path d="M70 65V560"/>
      </g>
      {bars}
      <path d="M75 525C155 517 205 493 275 466S390 426 448 373S565 308 625 230S700 145 735 60" fill="none" stroke="#32b5ff" stroke-width="7" filter="url(#growthGlow)"/>
      <g fill="#c5f2ff">
        <circle cx="75" cy="525" r="7"/><circle cx="205" cy="493" r="7"/><circle cx="390" cy="426" r="7"/><circle cx="565" cy="308" r="7"/><circle cx="700" cy="145" r="7"/>
      </g>
      <path d="M714 73l23-16-1 29" fill="#8ad5ff"/>
      <g fill="none" stroke="#1578af" opacity=".55">
        <path d="M62 580H250M62 605H205M620 575H745M650 600H745"/>
      </g>
    </svg>'''


def svg_globe() -> str:
    return '''
    <svg viewBox="0 0 720 720" class="art-svg globe-svg" aria-hidden="true">
      <defs>
        <radialGradient id="earth"><stop stop-color="#0b91db" stop-opacity=".72"/><stop offset=".72" stop-color="#063b66" stop-opacity=".5"/><stop offset="1" stop-color="#020a12" stop-opacity=".25"/></radialGradient>
        <filter id="globeGlow"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <circle cx="360" cy="360" r="305" fill="url(#earth)" stroke="#2ea7ff" stroke-width="3" filter="url(#globeGlow)"/>
      <g fill="none" stroke="#6fd1ff" stroke-width="2" opacity=".42">
        <ellipse cx="360" cy="360" rx="305" ry="105"/><ellipse cx="360" cy="360" rx="305" ry="205"/>
        <ellipse cx="360" cy="360" rx="125" ry="305"/><ellipse cx="360" cy="360" rx="225" ry="305"/>
      </g>
      <path d="M205 185l55 12 32 48 54 10 35 42-18 52-55 18-25 58-59-16-35-61-49-23 10-75zM420 250l58-38 78 27 31 47-24 45-61 10-25 50-52-20-30-53zM410 455l62-26 60 35-18 73-76 37-55-41z" fill="#2ea7ff" opacity=".42"/>
      <g fill="#84dcff" opacity=".6">
        <circle cx="175" cy="220" r="4"/><circle cx="230" cy="155" r="3"/><circle cx="580" cy="170" r="4"/><circle cx="620" cy="270" r="3"/>
        <circle cx="160" cy="510" r="4"/><circle cx="565" cy="565" r="4"/>
      </g>
    </svg>'''


def scene_html(manifest: dict, scene: dict, index: int, css: str) -> str:
    visual = scene["visual"]
    detail = esc(scene.get("detail") or "")
    title = storyboard_lines(scene)
    decor = circuit_svg(visual)

    if visual == "story-hook":
        body = f'''
          <section class="hook-title storyboard-title">{title}</section>
          <div class="hook-hud-label">AI / SYSTEMS / INFRASTRUCTURE</div>
        '''
    elif visual == "erp-cubes":
        body = f'''
          <section class="erp-copy">
            <div class="storyboard-title">{title}</div>
            <p>{detail}</p>
          </section>
          <section class="erp-art">{svg_cubes()}</section>
        '''
    elif visual == "decision-radar":
        body = f'''
          <section class="radar-copy"><div class="storyboard-title">{title}</div></section>
          <section class="radar-art">{svg_radar()}</section>
        '''
    elif visual == "agents-processes":
        body = f'''
          <section class="agents-copy"><div class="storyboard-title">{title}</div></section>
          <section class="agents-icons">
            <div class="process-icon"><div class="icon-disc">{icon_finance()}</div><div>ФИНАНСЫ</div></div>
            <div class="process-icon"><div class="icon-disc">{icon_logistics()}</div><div>ЛОГИСТИКА</div></div>
            <div class="process-icon support"><div class="icon-disc">{icon_support()}</div><div>ПОДДЕРЖКА<br>КЛИЕНТОВ</div></div>
          </section>
          {svg_agents_bg()}
        '''
    elif visual == "infra-growth":
        body = f'''
          <section class="growth-copy"><div class="storyboard-title">{title}</div></section>
          <section class="growth-art">{svg_growth()}</section>
          <div class="growth-hud"><span></span><span></span><span></span></div>
        '''
    elif visual == "cta-globe":
        body = f'''
          <section class="cta-copy">
            <div class="storyboard-title">{title}</div>
            <div class="cta-telegram"><span class="tg-icon">➤</span><span>ВСЕ ДЕТАЛИ<br>В TELEGRAM И НА САЙТЕ</span></div>
            <div class="cta-site">NEWS.CARNI.LTD</div>
            <div class="cta-channel">t.me/+KotqtD1F8EEwZDli</div>
          </section>
          <section class="cta-art">{svg_globe()}</section>
        '''
    elif visual == "outro-brand":
        body = f'''
          <section class="outro-center">
            <div class="outro-ai">AI NEWS</div>
            <div class="outro-by">BY CARNI</div>
            <div class="outro-tagline">{detail}</div>
            <div class="outro-links">news.carni.ltd · t.me/+KotqtD1F8EEwZDli</div>
          </section>
        '''
    else:
        fail(f"Unsupported visual: {visual}")

    return f'''<!doctype html>
<html lang="{esc(manifest['lang'])}">
<head><meta charset="utf-8"><style>{css}</style></head>
<body>
  <div class="canvas">
    <main class="story-card visual-{esc(visual)}">
      {decor}
      <div class="corner corner-a"></div><div class="corner corner-b"></div>
      {body}
    </main>
  </div>
</body>
</html>'''


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
    zoom = (
        "zoompan=z='min(zoom+0.000035,1.006)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
        if index in (0, 6)
        else "zoompan=z='min(zoom+0.000055,1.009)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
    )
    run([
        ffmpeg, "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(image_path),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", f"{duration:.3f}", "-vf", f"{zoom},format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "96k", "-shortest", str(output_path),
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

    with tempfile.TemporaryDirectory(prefix="carni-short-storyboard-") as tmp:
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
    print(f"Rendered {output_path} ({total:.1f}s, {WIDTH}x{HEIGHT}, storyboard-faithful v2)")


if __name__ == "__main__":
    main()
