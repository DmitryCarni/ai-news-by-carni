#!/usr/bin/env python3
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

WIDTH, HEIGHT, FPS = 1080, 1920, 30
ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "shorts" / "schema" / "manifest.schema.json"
STYLE = ROOT / "shorts" / "renderer" / "style.css"


def fail(msg: str) -> None:
    raise SystemExit(msg)


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode:
        sys.stderr.write(p.stdout + p.stderr)
        fail("Command failed: " + " ".join(cmd))


def chrome_path() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    fail("Chrome/Chromium is required")


def esc(v: object) -> str:
    return html.escape(str(v), quote=True)


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        fail("Manifest validation failed:\n- " + "\n- ".join(f"{'.'.join(map(str,e.absolute_path)) or '<root>'}: {e.message}" for e in errors))
    total = sum(float(s["duration"]) for s in data["scenes"])
    if len(data["scenes"]) != 6:
        fail("Storyboard v2 requires exactly 6 scenes")
    if not 38 <= total <= 42:
        fail(f"Storyboard v2 must be 38–42 seconds, got {total:.1f}")
    return data


def title_html(scene: dict) -> str:
    return "".join(f'<span class="line {esc(x.get("accent","none"))}">{esc(x["text"])}</span>' for x in scene["title"])


def copy_html(lines: list[str]) -> str:
    return "<br>".join(esc(x) for x in lines)


def hud_svg(color: str = "#2ea7ff") -> str:
    return f'''<svg class="hud" viewBox="0 0 1080 1920" aria-hidden="true">
      <g fill="none" stroke="{color}" stroke-width="2" opacity=".22">
        <path d="M20 170H150V230H230M20 360H110V430H205M18 660H160V610H245M20 1100H130V1180H230M20 1430H170V1370H260"/>
        <path d="M1060 210H920V280H835M1060 480H950V545H850M1060 760H915V705H820M1060 1180H930V1250H835M1060 1500H900V1440H810"/>
        <circle cx="150" cy="230" r="5"/><circle cx="110" cy="430" r="4"/><circle cx="920" cy="280" r="5"/><circle cx="950" cy="545" r="4"/>
        <path d="M90 80H320M760 80H990M90 1840H320M760 1840H990"/>
      </g>
    </svg>'''


def earth_svg() -> str:
    return '''<svg class="earth" viewBox="0 0 1200 700" aria-hidden="true">
      <defs><radialGradient id="eg"><stop stop-color="#127ac2"/><stop offset=".58" stop-color="#06375c"/><stop offset="1" stop-color="#01080e"/></radialGradient><filter id="gl"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      <ellipse cx="600" cy="540" rx="590" ry="330" fill="url(#eg)" stroke="#2ea7ff" stroke-width="4" filter="url(#gl)"/>
      <g fill="none" stroke="#64c7ff" opacity=".34" stroke-width="2"><ellipse cx="600" cy="540" rx="510" ry="120"/><ellipse cx="600" cy="540" rx="390" ry="250"/><path d="M110 500C300 420 900 420 1090 500M160 610C360 530 840 530 1040 610"/></g>
      <g fill="#2ea7ff" opacity=".7"><circle cx="220" cy="470" r="5"/><circle cx="365" cy="420" r="4"/><circle cx="570" cy="455" r="5"/><circle cx="780" cy="430" r="4"/><circle cx="960" cy="490" r="5"/></g>
    </svg>'''


def datacenter_svg() -> str:
    rows=[]
    for x in (90,255,420,585):
        rows.append(f'<rect x="{x}" y="80" width="125" height="470" rx="8" fill="#04111c" stroke="#0f6ea9" stroke-width="3"/>')
        for y in range(110,520,42):
            rows.append(f'<rect x="{x+17}" y="{y}" width="91" height="23" rx="3" fill="#06233a" stroke="#168dd2"/><circle cx="{x+95}" cy="{y+11}" r="4" fill="#39b8ff"/>')
    return f'''<svg viewBox="0 0 800 650" aria-hidden="true"><defs><radialGradient id="dc"><stop stop-color="#0a6098" stop-opacity=".55"/><stop offset="1" stop-opacity="0"/></radialGradient></defs><rect width="800" height="650" fill="url(#dc)" opacity=".6"/>{''.join(rows)}<path d="M60 585H740" stroke="#2ea7ff" stroke-width="3" opacity=".55"/></svg>'''


def chips_svg() -> str:
    return '''<svg viewBox="0 0 900 650" aria-hidden="true">
      <defs><filter id="cg"><feGaussianBlur stdDeviation="10" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      <g transform="translate(80 120) rotate(-8 250 180)" filter="url(#cg)"><rect width="350" height="280" rx="22" fill="#132208" stroke="#9edf41" stroke-width="5"/><rect x="60" y="55" width="230" height="170" rx="12" fill="#1e3510" stroke="#b8f06f" stroke-width="3"/><text x="175" y="145" text-anchor="middle" font-size="42" fill="#b9f45f" font-family="DejaVu Sans" font-weight="900">NVIDIA</text></g>
      <g transform="translate(470 170) rotate(8 170 150)" filter="url(#cg)"><rect width="330" height="260" rx="22" fill="#2b1609" stroke="#f39a3f" stroke-width="5"/><rect x="52" y="52" width="226" height="156" rx="12" fill="#3a1b08" stroke="#ffb45c" stroke-width="3"/><text x="165" y="142" text-anchor="middle" font-size="38" fill="#ffbe68" font-family="DejaVu Sans" font-weight="900">MEDIATEK</text></g>
      <path d="M390 300C430 240 465 260 515 315" fill="none" stroke="#72c8ff" stroke-width="7" stroke-dasharray="12 10"/>
    </svg>'''


def warning_svg() -> str:
    return '''<svg viewBox="0 0 300 300" aria-hidden="true"><defs><filter id="wg"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><path d="M150 30L278 260H22z" fill="#2b0505" stroke="#ff3b3b" stroke-width="8" filter="url(#wg)"/><text x="150" y="205" text-anchor="middle" font-size="150" fill="#ff4b4b" font-family="DejaVu Sans" font-weight="900">!</text></svg>'''


def finance_svg() -> str:
    bars=''.join(f'<rect x="{50+i*48}" y="{430-h}" width="26" height="{h}" fill="#08263c" stroke="#1e88c7"/>' for i,h in enumerate((40,65,80,110,95,150,190,240,300)))
    return f'''<svg viewBox="0 0 600 760" aria-hidden="true"><g opacity=".9">{bars}<path d="M40 410C100 390 130 350 180 360S250 305 300 300 370 250 420 180 495 145 550 90" fill="none" stroke="#2ea7ff" stroke-width="7"/><path d="M350 420C410 390 430 370 465 340S515 310 550 250" fill="none" stroke="#ff3b3b" stroke-width="5"/></g><g transform="translate(55 440)"><path d="M250 10l220 80H30z" fill="#9ba8b1"/><rect x="55" y="90" width="390" height="34" fill="#c8d1d7"/>{''.join(f'<rect x="{80+i*82}" y="124" width="48" height="190" fill="#9aa7b0"/>' for i in range(5))}<rect x="45" y="314" width="410" height="34" fill="#c8d1d7"/><rect x="25" y="348" width="450" height="28" fill="#7f8c95"/></g></svg>'''


def icon_svg(kind: str) -> str:
    if kind == "power":
        return '<svg viewBox="0 0 120 120"><path d="M68 8L28 66h29l-8 46 43-63H63z" fill="#2ea7ff"/></svg>'
    if kind == "shield":
        return '<svg viewBox="0 0 120 120"><path d="M60 9l38 16v27c0 26-15 47-38 59-23-12-38-33-38-59V25z" fill="none" stroke="#2ea7ff" stroke-width="8"/><path d="M60 35l8 15 17 3-12 12 3 18-16-8-16 8 3-18-12-12 17-3z" fill="#2ea7ff"/></svg>'
    return '<svg viewBox="0 0 120 120"><rect x="20" y="19" width="80" height="24" rx="5" fill="none" stroke="#2ea7ff" stroke-width="7"/><rect x="20" y="49" width="80" height="24" rx="5" fill="none" stroke="#2ea7ff" stroke-width="7"/><rect x="20" y="79" width="80" height="24" rx="5" fill="none" stroke="#2ea7ff" stroke-width="7"/><circle cx="86" cy="31" r="4" fill="#8ad5ff"/><circle cx="86" cy="61" r="4" fill="#8ad5ff"/><circle cx="86" cy="91" r="4" fill="#8ad5ff"/></svg>'


def scene_body(manifest: dict, s: dict) -> str:
    t = title_html(s)
    body = copy_html(s.get("body", []))
    v = s["visual"]
    if v == "earth-hook":
        return f'''{hud_svg()}<div class="content"><div class="title hook-title">{t}</div><div class="body-copy hook-copy">{body}</div><div class="brand hook-brand"><div class="ai">AI NEWS</div><div class="by">BY CARNI</div></div></div><div class="earth-wrap">{earth_svg()}</div>'''
    if v == "lambda-datacenter":
        return f'''{hud_svg()}<div class="content"><div class="title infra-title">{t}</div><div class="body-copy infra-copy">{body}</div><div class="datacenter">{datacenter_svg()}</div><div class="lambda-badge"><div class="badge money">$35B</div><div class="badge">λ Lambda</div></div><div class="infra-callout">{esc(s.get("callout",""))}</div></div>'''
    if v == "nvlink-chips":
        return f'''{hud_svg("#6fa63a")}<div class="content"><div class="title chip-title">{t}</div><div class="chip-stage">{chips_svg()}</div><div class="body-copy chip-copy">{body}</div></div>'''
    if v == "claude-security":
        terminal = ''.join(f'&gt; {esc(x)}<br>' for x in s.get("terminal", []))
        return f'''{hud_svg("#ff3535")}<div class="content"><div class="title security-title">{t}</div><div class="terminal">{terminal}</div><div class="warn">{warning_svg()}</div><div class="body-copy security-copy">{body}</div><div class="security-callout">{esc(s.get("callout",""))}</div></div>'''
    if v == "financial-risk":
        return f'''{hud_svg()}<div class="content"><div class="title finance-title">{t}</div><div class="body-copy finance-copy">{body}</div><div class="finance-stage">{finance_svg()}</div><div class="finance-callout">{esc(s.get("callout",""))}</div></div>'''
    if v == "race-cta":
        pillars=''.join(f'<div class="pillar"><div class="disc">{icon_svg(x["icon"])}</div>{esc(x["label"])}</div>' for x in s.get("items", []))
        return f'''{hud_svg()}<div class="content"><div class="title cta-title">{t}</div><div class="pillars">{pillars}</div><div class="body-copy cta-copy">{body}</div><div class="brand cta-brand"><div class="ai">AI NEWS</div><div class="by">BY CARNI</div></div><div class="cta-bar"><span>NEWS.CARNI.LTD</span><span class="icons"><span class="round">➤</span><span class="round">◎</span></span></div></div>{earth_svg()}'''
    fail(f"Unsupported visual: {v}")


def page_html(manifest: dict, scene: dict, css: str) -> str:
    return f'''<!doctype html><html lang="{esc(manifest['lang'])}"><head><meta charset="utf-8"><style>{css}</style></head><body><div class="canvas"><main class="scene"><div class="frame">{scene_body(manifest, scene)}</div></main></div></body></html>'''


def screenshots(manifest: dict, work: Path) -> list[Path]:
    css = STYLE.read_text(encoding="utf-8")
    imgs=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=chrome_path(),headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
        page=browser.new_page(viewport={"width":WIDTH,"height":HEIGHT},device_scale_factor=1)
        for i,s in enumerate(manifest["scenes"]):
            page.set_content(page_html(manifest,s,css),wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(80)
            out=work/f"scene-{i:02d}.png"
            page.screenshot(path=str(out),full_page=False)
            imgs.append(out)
        browser.close()
    return imgs


def segment(ffmpeg: str, image: Path, duration: float, out: Path, index: int) -> None:
    zoom="zoompan=z='min(zoom+0.00003,1.006)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"
    run([ffmpeg,"-y","-loop","1","-framerate",str(FPS),"-i",str(image),"-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=48000","-t",f"{duration:.3f}","-vf",f"{zoom},format=yuv420p","-c:v","libx264","-preset","medium","-crf","18","-r",str(FPS),"-c:a","aac","-b:a","96k","-shortest",str(out)])


def concat(ffmpeg: str, parts: list[Path], out: Path, work: Path) -> None:
    txt=work/"concat.txt"
    txt.write_text(''.join(f"file '{p.as_posix()}'\n" for p in parts),encoding="utf-8")
    run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-movflags","+faststart",str(out)])


def validate(ffprobe: str, out: Path) -> None:
    p=subprocess.run([ffprobe,"-v","error","-select_streams","v:0","-show_entries","stream=codec_name,width,height,r_frame_rate","-of","json",str(out)],text=True,capture_output=True,check=True)
    st=(json.loads(p.stdout).get("streams") or [{}])[0]
    if st.get("codec_name")!="h264" or st.get("width")!=WIDTH or st.get("height")!=HEIGHT:
        fail(f"Bad output stream: {st}")


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("manifest",type=Path)
    ap.add_argument("--output-dir",type=Path,default=Path("build/shorts"))
    args=ap.parse_args()
    manifest=load_manifest(args.manifest)
    ffmpeg=shutil.which("ffmpeg") or fail("ffmpeg required")
    ffprobe=shutil.which("ffprobe") or fail("ffprobe required")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    out=args.output_dir/f"{manifest['id']}.mp4"
    with tempfile.TemporaryDirectory(prefix="carni-short-") as tmp:
        work=Path(tmp)
        imgs=screenshots(manifest,work)
        parts=[]
        for i,(img,s) in enumerate(zip(imgs,manifest["scenes"])):
            part=work/f"part-{i:02d}.mp4"
            segment(ffmpeg,img,float(s["duration"]),part,i)
            parts.append(part)
        concat(ffmpeg,parts,out,work)
    validate(ffprobe,out)
    print(out)

if __name__ == "__main__":
    main()
