import math
import random
import wave
import struct
import shutil
import subprocess
from pathlib import Path

SR = 44100
BPM = 130
BEAT = 60.0 / BPM
BAR = BEAT * 4
TOTAL_BARS = 80
DURATION = TOTAL_BARS * BAR
OUT = Path("output")
OUT.mkdir(exist_ok=True)

random.seed(1337)

# Original composition for SACRIFICE.
# Dark house/electro, D minor. Two drops; Drop 2 is the larger evolution.
# No generative AI audio is used: every note, rhythm and synth is defined here.

buf = [0.0] * int((DURATION + 2.0) * SR)

def add_sample(t, value):
    i = int(t * SR)
    if 0 <= i < len(buf):
        buf[i] += value

def env_decay(x, decay):
    return math.exp(-x * decay)

def kick(t, amp=0.8):
    length = 0.30
    n = int(length * SR)
    phase = 0.0
    for j in range(n):
        x = j / SR
        f = 145 * math.exp(-x * 22) + 42
        phase += 2 * math.pi * f / SR
        y = math.sin(phase) * env_decay(x, 13)
        y += 0.12 * math.sin(phase * 2) * env_decay(x, 20)
        add_sample(t + x, amp * y)

def snare(t, amp=0.28):
    n = int(0.18 * SR)
    for j in range(n):
        x = j / SR
        noise = random.uniform(-1, 1)
        tone = math.sin(2 * math.pi * 190 * x)
        y = (0.82 * noise + 0.18 * tone) * env_decay(x, 25)
        add_sample(t + x, amp * y)

def hat(t, amp=0.12, open_hat=False):
    length = 0.13 if open_hat else 0.055
    decay = 30 if open_hat else 75
    n = int(length * SR)
    for j in range(n):
        x = j / SR
        noise = random.uniform(-1, 1)
        y = noise * env_decay(x, decay)
        add_sample(t + x, amp * y)

def osc(kind, phase):
    if kind == "sine":
        return math.sin(phase)
    if kind == "square":
        return 1.0 if math.sin(phase) >= 0 else -1.0
    # soft saw
    p = (phase / (2 * math.pi)) % 1.0
    return 2.0 * p - 1.0

def synth_note(t, dur, freq, amp, kind="saw", cutoff=2200, attack=0.008, release=0.12):
    n = int(dur * SR)
    phase = 0.0
    last = 0.0
    for j in range(n):
        x = j / SR
        if x < attack:
            e = x / attack
        elif x > dur - release:
            e = max(0.0, (dur - x) / release)
        else:
            e = 1.0
        phase += 2 * math.pi * freq / SR
        raw = osc("saw" if kind == "saw" else kind, phase)
        # Cheap one-pole low-pass to keep the synth smooth.
        a = min(0.98, max(0.02, 2 * math.pi * cutoff / SR))
        last += a * (raw - last)
        add_sample(t + x, amp * e * last)

def pad_chord(t, dur, freqs, amp=0.055):
    for k, f in enumerate(freqs):
        synth_note(t, dur, f, amp / max(1, len(freqs)), "saw", 1100, 0.15, 0.35)

def freq(note):
    names = {"C":0,"Cs":1,"D":2,"Ds":3,"E":4,"F":5,"Fs":6,"G":7,"Gs":8,"A":9,"As":10,"B":11}
    letter = note[:-1]
    octave = int(note[-1])
    midi = 12 * (octave + 1) + names[letter]
    return 440.0 * 2 ** ((midi - 69) / 12)

# D minor palette
CHORDS = [
    [freq("D3"), freq("F3"), freq("A3")],
    [freq("Bb2"), freq("D3"), freq("F3")],
    [freq("F2"), freq("A2"), freq("C3")],
    [freq("C3"), freq("E3"), freq("G3")],
]

# 0-15 intro, 16-31 drop 1, 32-47 break/build, 48-71 drop 2, 72-79 outro.
for bar in range(TOTAL_BARS):
    bt = bar * BAR
    chord = CHORDS[bar % 4]

    # Atmosphere/pads
    if bar < 16 or 32 <= bar < 48 or bar >= 72:
        pad_chord(bt, BAR * 1.05, chord, 0.045 if bar < 16 else 0.055)

    # Main beat
    if 16 <= bar < 32 or 48 <= bar < 72:
        intensity = 0.82 if bar < 48 else 1.0
        for b in range(4):
            kick(bt + b * BEAT, 0.72 * intensity)
        snare(bt + BEAT, 0.25 * intensity)
        snare(bt + 3 * BEAT, 0.30 * intensity)
        for h in range(8):
            hat(bt + h * BEAT / 2, 0.105 * intensity, h in (3, 7) and bar >= 50)

    # Intro pulse / tension
    if bar < 16:
        for p in range(4):
            synth_note(bt + p * BEAT, BEAT * 0.7, chord[0] / 2, 0.035, "sine", 500, 0.03, 0.18)

    # Bass: restrained first drop, fuller second drop
    if 16 <= bar < 32 or 48 <= bar < 72:
        notes = [chord[0] / 2, chord[0] / 2, chord[1] / 2, chord[2] / 2]
        for b, f in enumerate(notes):
            dur = BEAT * (0.75 if bar < 48 else 0.9)
            synth_note(bt + b * BEAT, dur, f, 0.19 if bar < 48 else 0.25, "saw", 420 if bar < 48 else 600, 0.005, 0.08)

    # Main motif. Kept identical in contour, then transformed in Drop 2.
    motif = ["D4","F4","Eb4","D4","Bb3","D4","C4","Bb3"]
    starts = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    if 16 <= bar < 32:
        for s, nn in zip(starts, motif):
            synth_note(bt + s * BEAT, BEAT * 0.34, freq(nn), 0.105, "saw", 1900, 0.006, 0.08)
    elif 48 <= bar < 72:
        # Stronger second drop: same identity, octave lift and altered ending.
        motif2 = ["D5","F5","Eb5","D5","Bb4","D5","F5","C5"]
        for s, nn in zip(starts, motif2):
            synth_note(bt + s * BEAT, BEAT * 0.38, freq(nn), 0.15, "saw", 2600, 0.004, 0.08)
        # Counter line only in Drop 2.
        counter = [(0.0,"A4"),(1.0,"Ab4"),(2.0,"G4"),(3.0,"F4")]
        for s, nn in counter:
            synth_note(bt + s * BEAT, BEAT * 0.45, freq(nn), 0.055, "square", 1500, 0.01, 0.1)

    # Build: rising notes and denser hats.
    if 40 <= bar < 48:
        for step in range(8):
            f = freq(["D4","Eb4","F4","G4","A4","Bb4","C5","D5"][step])
            synth_note(bt + step * BEAT / 2, BEAT * 0.25, f, 0.035 + step * 0.006, "saw", 2200, 0.002, 0.04)
        for h in range(16):
            hat(bt + h * BEAT / 4, 0.045 + h * 0.002)

    # Breakdown: isolated heartbeat-like kicks.
    if 32 <= bar < 40:
        kick(bt, 0.22)
        if bar in (35, 39):
            snare(bt + 3 * BEAT, 0.10)

# Master normalization and soft clipping.
peak = max(0.001, max(abs(x) for x in buf))
gain = 0.82 / peak
frames = bytearray()
for x in buf:
    y = math.tanh(x * gain * 1.05)
    frames += struct.pack("<h", int(max(-1, min(1, y)) * 32767))

wav_path = OUT / "SACRIFICE.wav"
with wave.open(str(wav_path), "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(frames)

mp3_path = OUT / "SACRIFICE.mp3"
ffmpeg = shutil.which("ffmpeg")
if ffmpeg:
    subprocess.run([
        ffmpeg, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3_path)
    ], check=True)
    print(f"Created {wav_path} and {mp3_path}")
else:
    print(f"Created {wav_path}. Install ffmpeg to also create MP3.")
