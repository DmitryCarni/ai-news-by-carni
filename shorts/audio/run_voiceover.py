#!/usr/bin/env python3
"""Run Shorts voiceover with a fixed, reproducible ElevenLabs pilot voice."""

import os

import add_voiceover

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_VOICE_NAME = "George"


def fixed_voice(_api_key: str) -> tuple[str, str]:
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_VOICE_ID
    name = "ELEVENLABS_VOICE_ID override" if voice_id != DEFAULT_VOICE_ID else DEFAULT_VOICE_NAME
    print(f"Using fixed ElevenLabs voice: {name} ({voice_id})")
    return voice_id, name


add_voiceover.choose_voice = fixed_voice

if __name__ == "__main__":
    add_voiceover.main()
