#!/usr/bin/env python3
"""
render_pacer.py
Frame-exact slow-paced breathing (SPB) pacer videos, generated from code.

Why code instead of hand-keyframing: every frame's position is computed from the
published parameters below, so the timing is exact (4.000 s = 120 frames,
6.000 s = 180 frames at 30 fps) and anyone can regenerate the identical file.

Usage:
    python3 render_pacer.py full     # full session example (intro + practice + 10:00 + end)
    python3 render_pacer.py previews # 60-s previews of all five visual styles

Requires: Python 3, numpy, Pillow, ffmpeg (libx264 + aac).
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- parameters
FPS = 30
W, H = 1280, 720
INHALE_S = 4.0
EXHALE_S = 6.0
CYCLE_S = INHALE_S + EXHALE_S            # 10 s -> 6 cycles/min (0.1 Hz)
PACING_CYCLES = 60                        # 10:00 of paced breathing
PRACTICE_CYCLES = 3
INTRO_S = 60
END_S = 15
REMINDER_CYCLES = {18, 36}                # 0-based: cycles starting at 3:00 and 6:00

assert (INHALE_S * FPS).is_integer() and (EXHALE_S * FPS).is_integer()
F_IN, F_EX = int(INHALE_S * FPS), int(EXHALE_S * FPS)
F_CYCLE = F_IN + F_EX

# palette (dark, low-glare: comfortable for 10+ minutes of steady viewing)
BG     = np.array([0x1F, 0x2A, 0x33], np.float32)
GUIDE  = np.array([0x3A, 0x4A, 0x56], np.float32)
WELL   = np.array([0x26, 0x33, 0x3D], np.float32)
FG     = np.array([0x86, 0xAE, 0xC2], np.float32)
TEXT   = np.array([0xD8, 0xE0, 0xE4], np.float32)

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_REG = os.path.join(HERE, "fonts", "AtkinsonHyperlegible-Regular.ttf")
OUT = os.path.join(HERE, "videos")
TMP = os.path.join(HERE, "tmp")
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

# ---------------------------------------------------------------- timing model
def ease(x):
    """Raised-cosine easing: velocity is zero at turnarounds, so motion feels
    like natural airflow without introducing an actual pause."""
    return 0.5 - 0.5 * math.cos(math.pi * x)

def phase_at(frame_in_cycle):
    """Return (p, phase, frac): p in [0,1] = size/position of the pacer,
    phase = 'in'/'out', frac = fraction of the current phase elapsed."""
    k = frame_in_cycle % F_CYCLE
    if k < F_IN:
        frac = k / F_IN
        return ease(frac), "in", frac
    frac = (k - F_IN) / F_EX
    return 1.0 - ease(frac), "out", frac

# ---------------------------------------------------------------- drawing
Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
CX, CY = W / 2, 330.0
D_C = np.sqrt((X - CX) ** 2 + (Y - CY) ** 2)
ANG = (np.arctan2(X - CX, -(Y - CY)) % (2 * np.pi)) / (2 * np.pi)   # 0 at top, clockwise

def aa(d):                   # signed distance (negative inside) -> coverage
    return np.clip(0.5 - d, 0.0, 1.0)

def paint(img, alpha, color, opacity=1.0):
    a = (alpha * opacity)[..., None]
    img *= (1.0 - a); img += color * a

def sdf_box(cx, cy, hw, hh, r):
    qx = np.abs(X - cx) - (hw - r); qy = np.abs(Y - cy) - (hh - r)
    outside = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2)
    inside = np.minimum(np.maximum(qx, qy), 0)
    return outside + inside - r

R_MIN, R_MAX = 100.0, 265.0

def draw_circle(img, p, frac):
    paint(img, np.clip(1.0 - np.abs(D_C - R_MAX) / 1.2, 0, 1), GUIDE, 0.8)   # faint max-size guide
    paint(img, aa(D_C - (R_MIN + p * (R_MAX - R_MIN))), FG)

def draw_ball(img, p, frac):
    top, bot = 110.0, 570.0
    paint(img, aa(sdf_box(CX, (top + bot) / 2, 3, (bot - top) / 2 + 3, 3)), GUIDE)
    by = bot - p * (bot - top)
    paint(img, aa(np.sqrt((X - CX) ** 2 + (Y - by) ** 2) - 30), FG)

def draw_bar(img, p, frac):
    L, hh = 760.0, 20.0
    left = CX - L / 2
    paint(img, aa(sdf_box(CX, CY, L / 2, hh, hh)), GUIDE)
    w = 2 * hh + p * (L - 2 * hh)
    paint(img, aa(sdf_box(left + w / 2, CY, w / 2, hh, hh)), FG)

WIN = dict(cx=CX, cy=CY, hw=240.0, hh=240.0, r=28.0)
WIN_SDF = sdf_box(WIN["cx"], WIN["cy"], WIN["hw"], WIN["hh"], WIN["r"])
def draw_water(img, p, frac):
    inside = aa(WIN_SDF)
    paint(img, inside, WELL)
    paint(img, np.clip(1.0 - np.abs(WIN_SDF) / 1.2, 0, 1), GUIDE)
    bottom = WIN["cy"] + WIN["hh"]; height = 2 * WIN["hh"]
    level = bottom - (0.10 + p * 0.82) * height
    paint(img, inside * np.clip(Y - level + 0.5, 0, 1), FG)

R_ARC = 292.0
RING_TRACK = np.clip(2.0 - np.abs(D_C - R_ARC), 0, 1)
def draw_ring(img, p, frac):
    paint(img, RING_TRACK, GUIDE, 0.8)
    arc = RING_TRACK * np.clip((frac - ANG) * 400.0 + 0.5, 0, 1)   # sweeps once per phase
    paint(img, arc, FG, 0.9)
    paint(img, aa(D_C - (R_MIN + p * (R_MAX - 25 - R_MIN))), FG)

STYLES = {"circle": draw_circle, "ball": draw_ball, "bar": draw_bar,
          "water": draw_water, "ring": draw_ring}

# ---------------------------------------------------------------- text
_font_cache, _mask_cache = {}, {}
def font(size):
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(FONT_REG, size)
    return _font_cache[size]

def text_mask(lines, size, y_center, line_gap=1.35):
    key = (tuple(lines), size, y_center)
    if key in _mask_cache: return _mask_cache[key]
    m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m); f = font(size)
    total = size * line_gap * (len(lines) - 1)
    for i, s in enumerate(lines):
        y = y_center - total / 2 + i * size * line_gap
        d.text((W / 2, y), s, font=f, fill=255, anchor="mm")
    arr = np.asarray(m, np.float32) / 255.0
    _mask_cache[key] = arr
    return arr

LABEL_Y = 668

# ---------------------------------------------------------------- frames
def frame(style, p, frac, overlays=()):
    img = np.empty((H, W, 3), np.float32); img[:] = BG
    STYLES[style](img, p, frac)
    for lines, size, y, opacity in overlays:
        if opacity > 0: paint(img, text_mask(lines, size, y), TEXT, opacity)
    return np.clip(img + 0.5, 0, 255).astype(np.uint8).tobytes()

def encoder(path, lossless=True):
    v = ["-c:v", "libx264", "-qp", "0", "-preset", "ultrafast"] if lossless else \
        ["-c:v", "libx264", "-crf", "30", "-preset", "slow", "-tune", "animation"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", *v, "-pix_fmt", "yuv420p", path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)

def write_segment(name, frames, expected=None):
    path = os.path.join(TMP, name + ".mkv")
    if expected and os.path.exists(path + ".done"):      # resume support
        return path, expected
    enc = encoder(path); n = 0
    for fr in frames:
        enc.stdin.write(fr); n += 1
    enc.stdin.close(); enc.wait()
    open(path + ".done", "w").write(str(n))
    return path, n

def cycle_frames(style, label=False, caption=None):
    for k in range(F_CYCLE):
        p, ph, frac = phase_at(k)
        ov = []
        if label:
            ov.append((["Breathe in" if ph == "in" else "Breathe out"], 34, LABEL_Y, 1.0))
        if caption:
            t = k / FPS
            op = min(1.0, t / 1.0, (CYCLE_S - t) / 1.0)
            ov.append(([caption], 30, LABEL_Y, max(0.0, op)))
        yield frame(style, p, frac, ov)

def held_frames(style, cards):
    """cards: list of (seconds, lines). Pacer shown at rest; 0.5-s crossfades."""
    for secs, lines in cards:
        n = int(secs * FPS)
        for k in range(n):
            t = k / FPS
            op = min(1.0, t / 0.5, (secs - t) / 0.5)
            yield frame(style, 0.0, 0.0, [(lines, 34, 652, max(0.0, op))]) if lines else frame(style, 0.0, 0.0)

# ---------------------------------------------------------------- audio
SR = 48000
def tone(freq, dur, peak_db):
    t = np.arange(int(SR * dur)) / SR
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (10 ** (peak_db / 20)) * env * np.sin(2 * np.pi * freq * t)

def chime(peak_db=-20):
    t = np.arange(int(SR * 2.5)) / SR
    env = np.minimum(t / 0.01, 1) * np.exp(-t / 0.7)
    s = np.sin(2 * np.pi * 523.25 * t) + 0.5 * np.sin(2 * np.pi * 784.0 * t)
    return (10 ** (peak_db / 20)) * env * s / 1.5

def write_wav(path, total_s, events):
    buf = np.zeros(int(SR * total_s), np.float32)
    for start_s, sig in events:
        i = int(start_s * SR); buf[i:i + len(sig)] += sig[: len(buf) - i]
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())

# ---------------------------------------------------------------- builds
INTRO_CARDS = [
    (10, ["In the next 10 minutes, you'll breathe along with this circle."]),
    (12, ["As it grows, breathe in gently through your nose.",
          "As it shrinks, breathe out slowly."]),
    (12, ["Keep each breath light and comfortable.",
          "There's no need to breathe deeply."]),
    (10, ["Sit upright and keep your eyes on the circle."]),
    (11, ["If you feel dizzy or short of breath, breathe normally",
          "for a moment, then rejoin the circle."]),
    (5,  ["Let's practice three breaths together."]),
]
END_CARDS = [(8, ["You can return to your normal breathing."]),
             (7, ["The breathing exercise is complete. Please continue."])]
CAPTION = "Keep breathing gently with the circle"

def concat(paths, out_mp4, wav=None, final=True):
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        for p in paths: f.write(f"file '{p}'\n")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst]
    if wav: cmd += ["-i", wav]
    cmd += ["-map", "0:v"] + (["-map", "1:a", "-c:a", "aac", "-b:a", "48k", "-ac", "1"] if wav else ["-an"])
    cmd += ["-c:v", "libx264", "-crf", "30", "-preset", "medium", "-tune", "animation",
            "-g", str(F_CYCLE), "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-movflags", "+faststart", out_mp4]
    subprocess.run(cmd, check=True)

def build_full(style="circle"):
    intro, n_intro = write_segment("intro", held_frames(style, INTRO_CARDS), INTRO_S * FPS)
    prac, n_prac = write_segment("practice_cycle", cycle_frames(style, label=True), F_CYCLE)
    plain, _ = write_segment("plain_cycle", cycle_frames(style), F_CYCLE)
    remind, _ = write_segment("remind_cycle", cycle_frames(style, caption=CAPTION), F_CYCLE)
    end, n_end = write_segment("end", held_frames(style, END_CARDS), END_S * FPS)
    seq = [intro] + [prac] * PRACTICE_CYCLES + \
          [remind if c in REMINDER_CYCLES else plain for c in range(PACING_CYCLES)] + [end]
    total_s = INTRO_S + (PRACTICE_CYCLES + PACING_CYCLES) * CYCLE_S + END_S
    assert n_intro == INTRO_S * FPS and n_end == END_S * FPS
    pacing_start = INTRO_S + PRACTICE_CYCLES * CYCLE_S
    pacing_end = pacing_start + PACING_CYCLES * CYCLE_S

    # version A: silent pacing, single soft chime when pacing ends (recommended)
    wav_a = os.path.join(TMP, "audio_silent.wav")
    write_wav(wav_a, total_s, [(pacing_end, chime())])
    concat(seq, os.path.join(OUT, f"pacer_{style}_4-6_full_session_silent.mp4"), wav_a)

    # version B: same video + soft phase tones (for comparison only)
    ev = [(pacing_end, chime())]
    for c in range(PRACTICE_CYCLES + PACING_CYCLES):
        t0 = INTRO_S + c * CYCLE_S
        ev += [(t0, tone(392.0, 0.25, -26)), (t0 + INHALE_S, tone(293.7, 0.25, -26))]
    wav_b = os.path.join(TMP, "audio_tones.wav")
    write_wav(wav_b, total_s, ev)
    concat(seq, os.path.join(OUT, f"pacer_{style}_4-6_full_session_phase-tones.mp4"), wav_b)
    print(f"full session: {total_s:.0f} s; pacing {pacing_start:.0f}-{pacing_end:.0f} s")

def build_previews():
    for style in STYLES:
        lab, _ = write_segment(f"{style}_lab", cycle_frames(style, label=True), F_CYCLE)
        pl, _ = write_segment(f"{style}_plain", cycle_frames(style), F_CYCLE)
        concat([lab] * 3 + [pl] * 3, os.path.join(OUT, f"preview_{style}_4-6_60s.mp4"))
        print("preview", style)

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "previews"
    if what in ("full", "all"): build_full("circle")
    if what in ("previews", "all"): build_previews()
