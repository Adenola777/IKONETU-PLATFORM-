"""Composes the music for the tour of the sample profile on the IkonetU home page.

Written for IkonetU Technology Limited on 21 October 2026. Every sound is synthesised here from sine waves and
noise, so the track uses no recording, sample or loop by anyone else, and IkonetU owns it. It needs numpy and
scipy, which the app itself does not use, and ffmpeg with libmp3lame.

    python3 compose_tour_music.py out_dir

writes out_dir/tour-music.wav and out_dir/tour-music.mp3: 16 bars at 84 beats a minute, about 46 seconds,
which loop without a seam because the reverb tail of the last bar is folded back onto the first.
"""
import subprocess
import sys
import wave

import numpy as np
from scipy.signal import butter, lfilter

SR = 44100
BPM = 84
BEAT = 60 / BPM
BAR = 4 * BEAT
BARS = 16
LOOP = BARS * BAR
TAIL = 5.0
N = int((LOOP + TAIL) * SR)
rng = np.random.default_rng(20261021)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def place(buf, start, sound):
    i = int(start * SR)
    j = min(len(buf), i + len(sound))
    buf[i:j] += sound[: j - i]


def t_of(seconds):
    return np.arange(int(seconds * SR)) / SR


def pad(freq, dur):
    """A soft chord voice: four partials, two voices a few cents apart, a slow swell and a long release."""
    release = 1.6
    t = t_of(dur + release)
    out = np.zeros_like(t)
    for cents in (-4, 4):
        f = freq * 2 ** (cents / 1200)
        for k, a in ((1, 1.0), (2, 0.32), (3, 0.14), (4, 0.06)):
            out += a * np.sin(2 * np.pi * f * k * t + rng.uniform(0, 2 * np.pi))
    env = np.minimum(1, t / 0.9)
    env *= np.where(t > dur, np.exp(-(t - dur) / (release / 4)), 1)
    return out * env * (1 + 0.04 * np.sin(2 * np.pi * 0.35 * t))


def bass(freq, dur):
    t = t_of(dur + 0.6)
    tone = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t)
    env = np.minimum(1, t / 0.015) * np.exp(-t / 0.9)
    return tone * env


def bell(freq):
    """A struck tone from frequency modulation, with a ratio that gives a soft glass sound."""
    t = t_of(3.0)
    index = 1.6 * np.exp(-t / 0.35)
    tone = np.sin(2 * np.pi * freq * t + index * np.sin(2 * np.pi * 3.5 * freq * t))
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.9)
    return tone * env


def pluck(freq):
    t = t_of(0.8)
    tone = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * 2 * freq * t)
    return tone * np.minimum(1, t / 0.003) * np.exp(-t / 0.22)


def shaker():
    t = t_of(0.09)
    b, a = butter(2, 6000 / (SR / 2), btype="high")
    noise = lfilter(b, a, rng.standard_normal(len(t)))
    return noise * np.exp(-t / 0.025)


# Cmaj7, Am7, Fmaj7, G6: the bass note and a close voicing for the pad, as MIDI note numbers.
CHORDS = [(48, (60, 64, 67, 71)), (45, (57, 60, 64, 67)), (41, (53, 57, 60, 64)), (43, (55, 59, 62, 64))]

# The melody, bar by bar, as (beat, note): sixteen bars, the second eight a variation on the first.
MELODY = [
    [(0, 76), (1.5, 79), (3, 74)],
    [(0.5, 72), (2, 76), (3.5, 74)],
    [(0, 69), (1.5, 72), (3, 76)],
    [(0.5, 74), (2, 71), (3, 74)],
    [(0, 79), (1, 76), (2.5, 74), (3.5, 72)],
    [(0.5, 76), (2, 72), (3, 69)],
    [(0, 72), (1.5, 76), (2.5, 77), (3.5, 76)],
    [(0, 74), (2, 79), (3, 74)],
    [(0, 76), (1.5, 79), (2.5, 81), (3.5, 79)],
    [(0.5, 76), (2, 72), (3.5, 74)],
    [(0, 72), (1.5, 69), (3, 72)],
    [(0.5, 74), (2, 79), (3, 74)],
    [(0, 84), (1, 79), (2.5, 76), (3.5, 74)],
    [(0.5, 76), (2, 79), (3, 76)],
    [(0, 77), (1.5, 76), (2.5, 72), (3.5, 69)],
    [(0, 71), (2, 74), (3, 79)],
]

pads, low, lead, arps, perc = (np.zeros(N) for _ in range(5))
for bar in range(BARS):
    start = bar * BAR
    root, voicing = CHORDS[bar % 4]
    for note in voicing:
        place(pads, start, pad(hz(note), BAR))
    place(low, start, bass(hz(root), 2 * BEAT))
    place(low, start + 2 * BEAT, 0.7 * bass(hz(root), 2 * BEAT))
    for beat, note in MELODY[bar]:
        place(lead, start + beat * BEAT, bell(hz(note)))
    if bar >= 8:
        # The second half adds a quiet arpeggio of the chord in eighth notes, for lift.
        for step in range(8):
            place(arps, start + step * BEAT / 2, pluck(hz(voicing[(step * 3) % 4] + 12)))
    for step in range(8):
        place(perc, start + step * BEAT / 2, (1.0 if step % 2 else 0.45) * shaker())

b, a = butter(2, 1800 / (SR / 2))
pads = lfilter(b, a, pads)


def reverb(x, spread):
    """A Schroeder reverb: four combs in parallel, then two all-pass filters."""
    out = np.zeros_like(x)
    for d, g in ((1557, 0.84), (1617, 0.83), (1491, 0.85), (1422, 0.86)):
        d += spread
        out += lfilter([1.0], np.r_[1.0, np.zeros(d - 1), -g], x)
    out /= 4
    for d, g in ((225, 0.5), (556, 0.5)):
        d += spread // 4
        out = lfilter(np.r_[-g, np.zeros(d - 1), 1.0], np.r_[1.0, np.zeros(d - 1), -g], out)
    return out


dry = 0.28 * pads + 0.55 * low + 0.46 * lead + 0.10 * arps + 0.035 * perc
send = 0.28 * pads + 0.45 * lead + 0.10 * arps
left = dry + 0.32 * reverb(send, 0)
right = dry + 0.32 * reverb(send, 23)
stereo = np.stack([left, right], axis=1)
# Nothing below 50 Hz: laptop and phone speakers cannot play it, and it only takes headroom.
hb, ha = butter(2, 50 / (SR / 2), btype="high")
stereo = lfilter(hb, ha, stereo, axis=0)

# Fold the tail past the loop point back onto the start, so the end runs into the beginning without a seam.
loop_n = int(LOOP * SR)
stereo[: N - loop_n] += stereo[loop_n:]
stereo = stereo[:loop_n]

stereo = np.tanh(1.2 * stereo / np.max(np.abs(stereo))) / np.tanh(1.2)
stereo *= 10 ** (-3 / 20)
rms = 20 * np.log10(np.sqrt(np.mean(stereo ** 2)))

out = sys.argv[1] if len(sys.argv) > 1 else "."
pcm = (stereo * 32767).astype("<i2")

with wave.open(f"{out}/tour-music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{out}/tour-music.wav", "-codec:a", "libmp3lame", "-b:a", "96k",
                f"{out}/tour-music.mp3"], check=True)
print(f"{LOOP:.2f} seconds, peak -3 dBFS, RMS {rms:.1f} dBFS")
