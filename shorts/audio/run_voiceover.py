#!/usr/bin/env python3
"""Run Shorts voiceover with a fixed ElevenLabs v3 pilot voice."""

import base64
import os
import urllib.parse
from pathlib import Path

import add_voiceover

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_VOICE_NAME = "George"


def fixed_voice(_api_key: str) -> tuple[str, str]:
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_VOICE_ID
    name = "ELEVENLABS_VOICE_ID override" if voice_id != DEFAULT_VOICE_ID else DEFAULT_VOICE_NAME
    print(f"Using fixed ElevenLabs voice: {name} ({voice_id})")
    return voice_id, name


def v3_tts_scene(
    api_key: str,
    voice_id: str,
    manifest: dict,
    scene_index: int,
    out_mp3: Path,
) -> tuple[dict, str]:
    cfg = manifest["tts"]
    text = manifest["scenes"][scene_index]["voiceover"]
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
    path = f"/v1/text-to-speech/{urllib.parse.quote(voice_id)}/with-timestamps?output_format=mp3_44100_128"
    data = add_voiceover.api_json("POST", path, api_key, payload)
    audio = data.get("audio_base64")
    if not audio:
        add_voiceover.fail(f"ElevenLabs returned no audio for scene {scene_index + 1}")
    out_mp3.write_bytes(base64.b64decode(audio))
    alignment = data.get("normalized_alignment") or data.get("alignment") or {}
    return alignment, add_voiceover.strip_audio_tags(text)


add_voiceover.choose_voice = fixed_voice
add_voiceover.tts_scene = v3_tts_scene

if __name__ == "__main__":
    add_voiceover.main()
