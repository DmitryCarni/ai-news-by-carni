#!/usr/bin/env python3
"""Add TTS voiceover and burned-in synchronized subtitles to a rendered Short."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import edge_tts


def fail(message: str) -> None:
    raise SystemExit(message)


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=cwd)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
        fail("Command failed: " + " ".join(cmd))
    return proc


def probe_duration(path: Path) -> float:
    proc = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1",
        str(path),
    ])
    return float(proc.stdout.strip())


def merge_srt_cues(raw_srt: str, max_words: int) -> str:
    """Merge timed edge-tts cues into compact readable subtitle phrases."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_srt.strip()) if b.strip()]
    cues: list[tuple[str, str, str]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if " --> " in line), None)
        if timing_index is None or timing_index + 1 >= len(lines):
            continue
        start, end = lines[timing_index].split(" --> ", 1)
        text = " ".join(lines[timing_index + 1:]).strip()
        if text:
            cues.append((start, end, text))

    if not cues:
        fail("TTS returned no parseable subtitle cues")

    merged: list[tuple[str, str, str]] = []
    group: list[tuple[str, str, str]] = []
    word_count = 0

    for cue in cues:
        cue_words = max(1, len(cue[2].split()))
        if group and word_count + cue_words > max_words:
            merged.append((group[0][0], group[-1][1], " ".join(x[2] for x in group)))
            group = []
            word_count = 0
        group.append(cue)
        word_count += cue_words

    if group:
        merged.append((group[0][0], group[-1][1], " ".join(x[2] for x in group)))

    return "\n\n".join(
        f"{index}\n{start} --> {end}\n{text}"
        for index, (start, end, text) in enumerate(merged, 1)
    ) + "\n"


def synthesize(manifest: dict, audio_path: Path, srt_path: Path) -> None:
    cfg = manifest["tts"]
    if cfg["provider"] != "edge-tts":
        fail(f"Unsupported TTS provider: {cfg['provider']}")

    communicate = edge_tts.Communicate(
        manifest["narration"],
        cfg["voice"],
        rate=cfg["rate"],
        volume=cfg["volume"],
        pitch=cfg["pitch"],
        boundary="WordBoundary",
    )
    submaker = edge_tts.SubMaker()

    with audio_path.open("wb") as audio:
        for chunk in communicate.stream_sync():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    raw_srt = submaker.get_srt().strip()
    if not raw_srt:
        fail("TTS returned no subtitle timing metadata")
    srt_path.write_text(merge_srt_cues(raw_srt, cfg["subtitle_words"]), encoding="utf-8")


def mux_and_burn(video_path: Path, audio_path: Path, srt_path: Path, total: float, output_path: Path, work: Path) -> None:
    voice_duration = probe_duration(audio_path)
    if voice_duration > total - 0.20:
        fail(
            f"Voiceover is too long for storyboard: {voice_duration:.2f}s > {total - 0.20:.2f}s. "
            "Increase TTS rate or shorten narration."
        )

    subtitle_filter = (
        "subtitles=captions.srt:"
        "force_style='FontName=DejaVu Sans,FontSize=15,"
        "PrimaryColour=&H00FFFFFF,BackColour=&H9800060B,"
        "OutlineColour=&HCC000000,BorderStyle=3,Outline=0,Shadow=0,"
        "Bold=1,Alignment=2,MarginL=95,MarginR=95,MarginV=205'"
    )

    run([
        "ffmpeg", "-y",
        "-i", str(video_path.resolve()),
        "-i", str(audio_path.resolve()),
        "-vf", subtitle_filter,
        "-af", f"apad=pad_dur={total:.3f}",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", f"{total:.3f}",
        "-movflags", "+faststart",
        str(output_path.resolve()),
    ], cwd=work)


def validate(path: Path, total: float) -> None:
    video = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate",
        "-of", "json", str(path),
    ]).stdout
    audio = run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels",
        "-of", "json", str(path),
    ]).stdout
    if '"codec_name": "h264"' not in video or '"width": 1080' not in video or '"height": 1920' not in video:
        fail("Voiced MP4 failed video validation")
    if '"codec_name": "aac"' not in audio:
        fail("Voiced MP4 failed audio validation")
    duration = probe_duration(path)
    if abs(duration - total) > 0.35:
        fail(f"Voiced MP4 duration mismatch: {duration:.2f}s vs {total:.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("build/shorts"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    total = sum(float(scene["duration"]) for scene in manifest["scenes"])
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    video_path = output_dir / f"{manifest['id']}.mp4"
    if not video_path.exists():
        fail(f"Base rendered MP4 not found: {video_path}")

    with tempfile.TemporaryDirectory(prefix="carni-short-audio-") as tmp:
        work = Path(tmp)
        audio_path = work / "voice.mp3"
        srt_path = work / "captions.srt"
        voiced_path = work / "voiced.mp4"

        synthesize(manifest, audio_path, srt_path)
        mux_and_burn(video_path, audio_path, srt_path, total, voiced_path, work)
        validate(voiced_path, total)

        shutil.copy2(srt_path, output_dir / f"{manifest['id']}.srt")
        shutil.move(str(voiced_path), str(video_path))

    print(f"Built voiced Short: {video_path}")


if __name__ == "__main__":
    main()
