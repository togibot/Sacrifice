# SACRIFICE — Original Music

Original procedural composition for the Geometry Dash level **SACRIFICE**.

## Concept

- Dark House / Electro
- Melancholic and unsettling atmosphere
- D minor
- 130 BPM
- Two main drops
- Drop 2 is a stronger evolution of Drop 1
- No generative AI audio
- Written as deterministic synthesis code

## Structure

- Bars 0–15: Intro / atmosphere
- Bars 16–31: Drop 1
- Bars 32–39: Breakdown
- Bars 40–47: Build
- Bars 48–71: Drop 2
- Bars 72–79: Outro

## Generate

Run:

```bash
python generate.py
```

This creates `output/SACRIFICE.wav`. If `ffmpeg` is installed, it also creates `output/SACRIFICE.mp3` at 192 kbps.

GitHub Actions also renders the audio automatically and stores the WAV/MP3 as a workflow artifact.
