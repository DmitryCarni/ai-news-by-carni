# AI News by Carni — Shorts Stage 1

Stage 1 proves the deterministic technical path:

`manifest.json → validate → draw scenes → FFmpeg → 1080×1920 MP4`

Editorial selection and wording happen before this pipeline. The renderer does not research, choose stories or rewrite conclusions.

## Current scope

- RU Daily pilot first;
- one strongest signal per Short;
- 30–45 seconds target;
- approved Carni Shorts v1 dark/cold-blue visual language;
- H.264 video + silent AAC track for Stage 1;
- MP4 is stored as a GitHub Actions artifact, not committed to Git;
- TTS, timed subtitles and platform publishing are later stages.

## Repository layout

```text
shorts/
  manifests/ru/daily/*.json
  renderer/render.py
  schema/manifest.schema.json
```

## Local build

Requirements: Python 3.12+, FFmpeg/ffprobe, DejaVu Sans, `pillow`, `jsonschema`.

```bash
python shorts/renderer/render.py \
  shorts/manifests/ru/daily/2026-08-30.json \
  --output-dir build/shorts
```

Expected output:

```text
build/shorts/2026-08-30-infrastructure-risk.mp4
```

A manifest push or renderer/schema change triggers `.github/workflows/shorts-build.yml`. The workflow renders all current manifests, validates the generated MP4 stream and uploads the result as a 14-day workflow artifact.
