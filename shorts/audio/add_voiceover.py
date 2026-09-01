#!/usr/bin/env python3
"""Add ElevenLabs v3 voiceover and scene-aware kinetic captions to a rendered Short."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.elevenlabs.io"
WIDTH, HEIGHT = 1080, 1920


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


def api_json(method: str, path: str, api_key: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_BASE + path,
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
            "User-Agent": "ai-news-by-carni-shorts/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        fail(f"ElevenLabs API error {exc.code}: {details[:1200]}")
    except urllib.error.URLError as exc:
        fail(f"ElevenLabs connection error: {exc}")


def choose_voice(api_key: str) -> tuple[str, str]:
    override = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if override:
        data = api_json("GET", f"/v1/voices/{urllib.parse.quote(override)}", api_key)
        name = data.get("name") or "ELEVENLABS_VOICE_ID override"
        return override, name

    query = urllib.parse.urlencode({
        "page_size": 100,
        "gender": "male",
        "include_total_count": "false",
    })
    data = api_json("GET", f"/v2/voices?{query}", api_key)
    voices = data.get("voices") or []
    if not voices:
        fail("ElevenLabs returned no available male voices. Set ELEVENLABS_VOICE_ID explicitly.")

    def score(voice: dict) -> tuple[int, str]:
        labels = voice.get("labels") or {}
        verified = voice.get("verified_languages") or []
        text = " ".join([
            str(voice.get("name") or ""),
            str(voice.get("description") or ""),
            " ".join(f"{k} {v}" for k, v in labels.items()),
        ]).lower()
        points = 0
        if "finley" in text:
            points += 100
        if any(k in text for k in ("anchor", "news", "social media")):
            points += 35
        if any(k in text for k in ("energetic", "dynamic", "upbeat", "expressive")):
            points += 28
        if any(k in text for k in ("articulate", "confident", "conversational", "narrator")):
            points += 18
        if any((item.get("language") or "").lower() in {"ru", "rus", "russian"} for item in verified if isinstance(item, dict)):
            points += 45
        if str(labels.get("language", "")).lower() in {"ru", "rus", "russian"}:
            points += 35
        if str(labels.get("age", "")).lower() in {"young", "middle aged", "middle-aged"}:
            points += 5
        if voice.get("category") in {"premade", "generated"}:
            points += 3
        return points, str(voice.get("name") or "")

    ranked = sorted(voices, key=score, reverse=True)
    chosen = ranked[0]
    chosen_id = chosen.get("voice_id")
    if not chosen_id:
        fail("Chosen ElevenLabs voice has no voice_id")
    preview = ", ".join(f"{v.get('name','?')}[{score(v)[0]}]" for v in ranked[:5])
    print(f"ElevenLabs voice candidates: {preview}")
    print(f"Chosen ElevenLabs voice: {chosen.get('name','?')} ({chosen_id})")
    return chosen_id, str(chosen.get("name") or chosen_id)


def strip_audio_tags(text: str) -> str:
    return re.sub(r"\[[^\]]+\]\s*", "", text).strip()


def tts_scene(
    api_key: str,
    voice_id: str,
    manifest: dict,
    scene_index: int,
    out_mp3: Path,
) -> tuple[dict, str]:
    cfg = manifest["tts"]
    scenes = manifest["scenes"]
    scene = scenes[scene_index]
    text = scene["voiceover"]
    previous_text = strip_audio_tags(scenes[scene_index - 1]["voiceover"]) if scene_index else None
    next_text = strip_audio_tags(scenes[scene_index + 1]["voiceover"]) if scene_index + 1 < len(scenes) else None

    payload = {
        "text": text,
        "model_id": cfg["model"],
        "language_code": "ru" if manifest["lang"] == "ru" else "en",
        "voice_settings": {
            "stability": cfg["stability"],
            "similarity_boost": cfg["similarity_boost"],
            "style": cfg["style"],
            "use_speaker_boost": True,
            "speed": cfg["speed"],
        },
        "seed": int(cfg["seed"]) + scene_index,
        "apply_text_normalization": "auto",
    }
    if previous_text:
        payload["previous_text"] = previous_text
    if next_text:
        payload["next_text"] = next_text

    path = f"/v1/text-to-speech/{urllib.parse.quote(voice_id)}/with-timestamps?output_format=mp3_44100_128"
    data = api_json("POST", path, api_key, payload)
    audio = data.get("audio_base64")
    if not audio:
        fail(f"ElevenLabs returned no audio for scene {scene_index + 1}")
    out_mp3.write_bytes(base64.b64decode(audio))
    alignment = data.get("normalized_alignment") or data.get("alignment") or {}
    return alignment, strip_audio_tags(text)


def atempo_filter(factor: float) -> str:
    factors: list[float] = []
    while factor > 2.0:
        factors.append(2.0)
        factor /= 2.0
    while factor < 0.5:
        factors.append(0.5)
        factor /= 0.5
    factors.append(factor)
    return ",".join(f"atempo={x:.6f}" for x in factors)


def fit_scene_audio(raw_mp3: Path, scene_duration: float, out_wav: Path) -> tuple[float, float]:
    raw_duration = probe_duration(raw_mp3)
    speech_target = max(0.5, scene_duration - 0.18)
    speed_factor = raw_duration / speech_target if raw_duration > speech_target else 1.0
    processed_speech_duration = raw_duration / speed_factor
    filters = []
    if speed_factor > 1.0005:
        filters.append(atempo_filter(speed_factor))
    filters.append(f"apad=pad_dur={scene_duration:.3f}")
    run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(raw_mp3),
        "-af", ",".join(filters),
        "-t", f"{scene_duration:.3f}",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
        str(out_wav),
    ])
    return raw_duration, processed_speech_duration


def words_from_alignment(alignment: dict, fallback_text: str, raw_duration: float) -> list[tuple[str, float, float]]:
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    if chars and len(chars) == len(starts) == len(ends):
        words: list[tuple[str, float, float]] = []
        buf: list[str] = []
        word_start: float | None = None
        word_end: float | None = None
        in_tag = False

        def flush() -> None:
            nonlocal buf, word_start, word_end
            text = "".join(buf).strip("-–—")
            if text and word_start is not None and word_end is not None:
                words.append((text, word_start, word_end))
            buf = []
            word_start = None
            word_end = None

        for ch, start, end in zip(chars, starts, ends):
            if ch == "[":
                flush()
                in_tag = True
                continue
            if ch == "]" and in_tag:
                in_tag = False
                continue
            if in_tag:
                continue
            if ch.isalnum() or ch in "$%+-/":
                if word_start is None:
                    word_start = float(start)
                word_end = float(end)
                buf.append(ch)
            else:
                flush()
        flush()
        if words:
            return words

    fallback_words = re.findall(r"[\w$%+\-/]+", fallback_text, flags=re.UNICODE)
    if not fallback_words:
        return []
    step = max(raw_duration, 0.1) / len(fallback_words)
    return [(word, i * step, (i + 1) * step) for i, word in enumerate(fallback_words)]


def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    centis = int(round(seconds * 100))
    h, rem = divmod(centis, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def caption_text(words: list[str]) -> str:
    if not words:
        return ""
    if len(words) == 1:
        return r"{\c&H00FFA72E&}" + ass_escape(words[0]) + r"{\c&H00FFFFFF&}"
    prefix = ass_escape(" ".join(words[:-1]))
    final = ass_escape(words[-1])
    return prefix + r" {\c&H00FFA72E&}" + final + r"{\c&H00FFFFFF&}"


def build_ass(manifest: dict, scene_infos: list[dict], out_ass: Path) -> None:
    cfg = manifest["tts"]
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Kinetic,DejaVu Sans Condensed,58,&H00FFFFFF,&H0000FFFF,&H00000000,&HA006131F,-1,0,0,0,100,100,0,0,3,0,0,5,70,70,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events: list[str] = []
    global_offset = 0.0

    for scene, info in zip(manifest["scenes"], scene_infos):
        duration = float(scene["duration"])
        if scene.get("caption_mode") != "kinetic":
            global_offset += duration
            continue

        raw_duration = info["raw_duration"]
        processed_duration = info["processed_speech_duration"]
        scale = processed_duration / raw_duration if raw_duration > 0 else 1.0
        words = words_from_alignment(info["alignment"], info["spoken_text"], raw_duration)
        group_size = int(cfg["caption_words"])
        y = int(scene["caption_y"])

        for i in range(0, len(words), group_size):
            group = words[i:i + group_size]
            if not group:
                continue
            start = global_offset + group[0][1] * scale
            end = global_offset + group[-1][2] * scale
            end = min(global_offset + duration - 0.08, max(end, start + 0.45))
            if end <= start:
                continue
            text = caption_text([w[0] for w in group])
            effect = rf"{{\an5\pos(540,{y})\fad(35,55)}}"
            events.append(
                f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Kinetic,,0,0,0,,{effect}{text}"
            )

        global_offset += duration

    out_ass.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")


def concat_audio(wavs: list[Path], out_wav: Path, work: Path) -> None:
    list_file = work / "audio-concat.txt"
    list_file.write_text(
        "\n".join("file '" + str(p.resolve()).replace("'", r"'\''") + "'" for p in wavs) + "\n",
        encoding="utf-8",
    )
    run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
        str(out_wav),
    ])


def mux_and_burn(video_path: Path, audio_path: Path, ass_path: Path, total: float, output_path: Path, work: Path) -> None:
    run([
        "ffmpeg", "-y",
        "-i", str(video_path.resolve()),
        "-i", str(audio_path.resolve()),
        "-vf", "ass=captions.ass",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k",
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
    cfg = manifest["tts"]
    if cfg["provider"] != "elevenlabs":
        fail(f"Unsupported TTS provider: {cfg['provider']}")

    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        fail("ELEVENLABS_API_KEY is required")

    total = sum(float(scene["duration"]) for scene in manifest["scenes"])
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / f"{manifest['id']}.mp4"
    if not video_path.exists():
        fail(f"Base rendered MP4 not found: {video_path}")

    voice_id, voice_name = choose_voice(api_key)

    with tempfile.TemporaryDirectory(prefix="carni-elevenlabs-") as tmp:
        work = Path(tmp)
        scene_infos: list[dict] = []
        wavs: list[Path] = []

        for index, scene in enumerate(manifest["scenes"]):
            raw_mp3 = work / f"scene-{index + 1:02d}.mp3"
            fitted_wav = work / f"scene-{index + 1:02d}.wav"
            alignment, spoken_text = tts_scene(api_key, voice_id, manifest, index, raw_mp3)
            raw_duration, processed_duration = fit_scene_audio(raw_mp3, float(scene["duration"]), fitted_wav)
            print(
                f"Scene {index + 1}: raw voice {raw_duration:.2f}s -> "
                f"{processed_duration:.2f}s speech inside {float(scene['duration']):.2f}s scene"
            )
            scene_infos.append({
                "alignment": alignment,
                "spoken_text": spoken_text,
                "raw_duration": raw_duration,
                "processed_speech_duration": processed_duration,
            })
            wavs.append(fitted_wav)

        full_voice = work / "voice.wav"
        ass_path = work / "captions.ass"
        voiced_path = work / "voiced.mp4"
        concat_audio(wavs, full_voice, work)
        build_ass(manifest, scene_infos, ass_path)
        mux_and_burn(video_path, full_voice, ass_path, total, voiced_path, work)
        validate(voiced_path, total)

        shutil.copy2(ass_path, output_dir / f"{manifest['id']}.ass")
        profile = {
            "provider": "elevenlabs",
            "model": cfg["model"],
            "voice_id": voice_id,
            "voice_name": voice_name,
            "settings": {
                "stability": cfg["stability"],
                "similarity_boost": cfg["similarity_boost"],
                "style": cfg["style"],
                "speed": cfg["speed"],
                "seed": cfg["seed"],
            },
            "caption_words": cfg["caption_words"],
            "caption_policy": "scene-aware kinetic captions; hook captions suppressed",
        }
        (output_dir / f"{manifest['id']}.voice.json").write_text(
            json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        shutil.move(str(voiced_path), str(video_path))

    print(f"Built ElevenLabs voiced Short: {video_path}")


if __name__ == "__main__":
    main()
