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
buf = [0.0] * int((DURATION + 2.0) * SR)

def add_sample(t, value):
    i = int(t * SR)
    if 0 <= i < len(buf): buf[i] += value

def env_decay(x, decay): return math.exp(-x * decay)

def kick(t, amp=0.8):
    n = int(0.30 * SR); phase = 0.0
    for j in range(n):
        x=j/SR; f=145*math.exp(-x*22)+42; phase += 2*math.pi*f/SR
        y=math.sin(phase)*env_decay(x,13)+0.12*math.sin(phase*2)*env_decay(x,20)
        add_sample(t+x,amp*y)

def snare(t, amp=0.28):
    n=int(.18*SR)
    for j in range(n):
        x=j/SR; noise=random.uniform(-1,1); tone=math.sin(2*math.pi*190*x)
        add_sample(t+x,amp*(.82*noise+.18*tone)*env_decay(x,25))

def hat(t, amp=.12, open_hat=False):
    length=.13 if open_hat else .055; decay=30 if open_hat else 75; n=int(length*SR)
    for j in range(n):
        x=j/SR; add_sample(t+x,amp*random.uniform(-1,1)*env_decay(x,decay))

def osc(kind, phase):
    if kind=="sine": return math.sin(phase)
    if kind=="square": return 1.0 if math.sin(phase)>=0 else -1.0
    p=(phase/(2*math.pi))%1.0
    return 2.0*p-1.0

def synth_note(t,dur,hz,amp,kind="saw",cutoff=2200,attack=.008,release=.12):
    n=int(dur*SR); phase=0.0; last=0.0
    a=min(.98,max(.02,2*math.pi*cutoff/SR))
    for j in range(n):
        x=j/SR
        e=x/attack if x<attack else max(0,(dur-x)/release) if x>dur-release else 1
        phase += 2*math.pi*hz/SR; raw=osc(kind,phase); last += a*(raw-last)
        add_sample(t+x,amp*e*last)

def freq(note):
    names={"C":0,"Cs":1,"D":2,"Ds":3,"E":4,"F":5,"Fs":6,"G":7,"Gs":8,"A":9,"As":10,"B":11}
    aliases={"Db":"Cs","Eb":"Ds","Gb":"Fs","Ab":"Gs","Bb":"As"}
    key=note[:-1]; octave=int(note[-1]); key=aliases.get(key,key)
    midi=12*(octave+1)+names[key]
    return 440.0*2**((midi-69)/12)

def pad_chord(t,dur,notes,amp=.055):
    for note in notes: synth_note(t,dur,freq(note),amp/len(notes),"saw",1100,.15,.35)

CHORDS=[["D3","F3","A3"],["Bb2","D3","F3"],["F2","A2","C3"],["C3","E3","G3"]]

for bar in range(TOTAL_BARS):
    bt=bar*BAR; chord=CHORDS[bar%4]
    # Dark atmosphere: sustained chords with no chiptune square layers.
    if bar<16 or 32<=bar<48 or bar>=72:
        pad_chord(bt,BAR*1.05,chord,.045 if bar<16 else .055)

    # DROP 1 / DROP 2 rhythm section.
    if 16<=bar<32 or 48<=bar<72:
        intensity=.82 if bar<48 else 1.0
        for b in range(4): kick(bt+b*BEAT,.72*intensity)
        snare(bt+BEAT,.25*intensity); snare(bt+3*BEAT,.30*intensity)
        for h in range(8): hat(bt+h*BEAT/2,.105*intensity,h in (3,7) and bar>=50)

    # Sub bass: sine only, avoiding square-wave 8-bit character.
    if bar<16:
        for p in range(4): synth_note(bt+p*BEAT,BEAT*.7,freq(chord[0])/2,.045,"sine",420,.03,.18)
    if 16<=bar<32 or 48<=bar<72:
        notes=[freq(chord[0])/2,freq(chord[0])/2,freq(chord[1])/2,freq(chord[2])/2]
        for b,hz in enumerate(notes):
            dur=BEAT*(.75 if bar<48 else .9)
            synth_note(bt+b*BEAT,dur,hz,.19 if bar<48 else .25,"saw",420 if bar<48 else 600,.005,.08)

    motif=["D4","F4","Eb4","D4","Bb3","D4","C4","Bb3"]
    starts=[0,.5,1,1.5,2,2.5,3,3.5]
    if 16<=bar<32:
        for s,nn in zip(starts,motif): synth_note(bt+s*BEAT,BEAT*.34,freq(nn),.105,"saw",1900,.006,.08)
    elif 48<=bar<72:
        motif2=["D5","F5","Eb5","D5","Bb4","D5","F5","C5"]
        for s,nn in zip(starts,motif2): synth_note(bt+s*BEAT,BEAT*.38,freq(nn),.15,"saw",2600,.004,.08)
        counter=[(0,"A4"),(1,"Ab4"),(2,"G4"),(3,"F4")]
        for s,nn in counter: synth_note(bt+s*BEAT,BEAT*.45,freq(nn),.055,"saw",1500,.01,.1)

    # Build-up: filtered saw notes and rising hats.
    if 40<=bar<48:
        scale=["D4","Eb4","F4","G4","A4","Bb4","C5","D5"]
        for step,nn in enumerate(scale): synth_note(bt+step*BEAT/2,BEAT*.25,freq(nn),.035+step*.006,"saw",2200,.002,.04)
        for h in range(16): hat(bt+h*BEAT/4,.045+h*.002)

    # Break: sparse kick and distant minor chord movement.
    if 32<=bar<40:
        kick(bt,.22)
        if bar in (35,39): snare(bt+3*BEAT,.10)

# Gentle saturation / normalization.
peak=max(.001,max(abs(x) for x in buf)); gain=.82/peak
frames=bytearray()
for x in buf:
    y=math.tanh(x*gain*1.05); frames += struct.pack("<h",int(max(-1,min(1,y))*32767))

wav_path=OUT/"SACRIFICE.wav"
with wave.open(str(wav_path),"wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(frames)

mp3_path=OUT/"SACRIFICE.mp3"
ffmpeg=shutil.which("ffmpeg")
if ffmpeg:
    subprocess.run([ffmpeg,"-y","-i",str(wav_path),"-codec:a","libmp3lame","-b:a","192k",str(mp3_path)],check=True)
    print(f"Created {wav_path} and {mp3_path}")
else:
    print(f"Created {wav_path}. Install ffmpeg to also create MP3.")
