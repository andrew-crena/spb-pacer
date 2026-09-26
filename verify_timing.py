#!/usr/bin/env python3
"""
verify_timing.py
Decodes a rendered pacer MP4 and measures the circle's diameter on every frame,
then checks the measured motion against the 4 s / 6 s model.

Usage: python3 verify_timing.py out/pacer_circle_4-6_full_session_silent.mp4
Writes timing_check.png and timing_check.csv next to the video.
"""
import json, subprocess, sys
import numpy as np
import render_pacer as R

path = sys.argv[1]
probe = json.loads(subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
     "-show_entries", "stream=nb_read_frames,r_frame_rate,width,height:format=duration",
     "-of", "json", path], capture_output=True, text=True, check=True).stdout)
st = probe["streams"][0]
n_frames, fps = int(st["nb_read_frames"]), st["r_frame_rate"]

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
                      f"format=gray,crop={R.W}:1:0:{int(R.CY)}", "-f", "rawvideo", "-"],
                     capture_output=True, check=True).stdout
rows = np.frombuffer(raw, np.uint8).reshape(-1, R.W).astype(np.float32)
assert rows.shape[0] == n_frames

# Subpixel diameter: interpolate where the row crosses 50% between background and circle
bg = float(np.median(rows[:, :50])); fg = float(np.median(rows[:, R.W // 2 - 10:R.W // 2 + 10]))
mid = (bg + fg) / 2
def row_diameter(r):
    idx = np.flatnonzero(r > mid)
    if len(idx) < 2: return 0.0
    a, b = idx[0], idx[-1]
    xl = a - (r[a] - mid) / max(r[a] - r[a - 1], 1e-6)
    xr = b + (r[b] - mid) / max(r[b] - r[b + 1], 1e-6)
    return xr - xl
diam = np.array([row_diameter(r) for r in rows])

start = int((R.INTRO_S + R.PRACTICE_CYCLES * R.CYCLE_S) * R.FPS)
k = np.arange(R.PACING_CYCLES * R.F_CYCLE)
model = np.array([2 * (R.R_MIN + R.phase_at(i)[0] * (R.R_MAX - R.R_MIN)) for i in k])
meas = diam[start:start + len(k)]
err = meas - model

# Phase lengths from the measurement alone, via level crossings (unbiased for the eased motion).
# On a raised-cosine rise, going from 25% to 75% of full size takes exactly one third of the phase,
# so phase length = 3 x (time between the 25% and 75% crossings). Same on the way down.
p_meas = (meas / 2 - R.R_MIN) / (R.R_MAX - R.R_MIN)
def crossing(seg, level, rising):
    s_ = seg - level
    idx = np.flatnonzero((s_[:-1] < 0) & (s_[1:] >= 0)) if rising else np.flatnonzero((s_[:-1] > 0) & (s_[1:] <= 0))
    i = idx[0]; return i + (-s_[i]) / (s_[i + 1] - s_[i])
inhale_s, exhale_s, rise50 = [], [], []
for c in range(R.PACING_CYCLES):
    seg = p_meas[c * R.F_CYCLE:(c + 1) * R.F_CYCLE]
    up, dn = seg[:R.F_IN + 5], seg[R.F_IN - 5:]
    inhale_s.append(3 * (crossing(up, .75, True) - crossing(up, .25, True)) / R.FPS)
    exhale_s.append(3 * (crossing(dn, .25, False) - crossing(dn, .75, False)) / R.FPS)
    rise50.append((c * R.F_CYCLE + crossing(up, .5, True)) / R.FPS)
inhale_s, exhale_s = np.array(inhale_s), np.array(exhale_s)
periods = np.diff(rise50)

report = {
    "file": path, "frames": n_frames, "frame_rate": fps,
    "duration_s": round(float(probe["format"]["duration"]), 3),
    "expected_frames": int((R.INTRO_S + (R.PRACTICE_CYCLES + R.PACING_CYCLES) * R.CYCLE_S + R.END_S) * R.FPS),
    "pacing_window_s": [start / R.FPS, (start + len(k)) / R.FPS],
    "diameter_error_px": {"mean": round(float(err.mean()), 2), "max_abs": round(float(np.abs(err).max()), 2)},
    "inhale_s": {"mean": round(float(inhale_s.mean()), 3), "min": round(float(inhale_s.min()), 3), "max": round(float(inhale_s.max()), 3)},
    "exhale_s": {"mean": round(float(exhale_s.mean()), 3), "min": round(float(exhale_s.min()), 3), "max": round(float(exhale_s.max()), 3)},
    "cycle_period_s": {"mean": round(float(periods.mean()), 4), "min": round(float(periods.min()), 4), "max": round(float(periods.max()), 4)},
    "breaths_per_min": round(60.0 / float(periods.mean()), 3),
}
print(json.dumps(report, indent=1))

base = path.rsplit(".", 1)[0]
np.savetxt(base + "_timing_check.csv", np.column_stack([k / R.FPS, model, meas]),
           delimiter=",", header="t_pacing_s,model_diameter_px,measured_diameter_px", comments="", fmt="%.4f")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, (a, b) = plt.subplots(2, 1, figsize=(9, 5.6), gridspec_kw={"height_ratios": [1.3, 1]})
n = 3 * R.F_CYCLE
a.plot(k[:n] / R.FPS, model[:n], color="#9aa7b0", lw=4, label="Model (4 s in, 6 s out)")
a.plot(k[:n] / R.FPS, meas[:n], color="#1f5f7a", lw=1.2, label="Measured from the MP4")
for c in range(3):
    a.axvspan(c * R.CYCLE_S, c * R.CYCLE_S + R.INHALE_S, color="#1f5f7a", alpha=0.07, lw=0)
a.set_xlabel("Seconds into the 10-minute pacing period"); a.set_ylabel("Circle diameter (px)")
a.set_title("First three breaths: measured motion matches the model", loc="left", fontsize=11)
a.legend(frameon=False, loc="lower right")
b.plot(np.arange(1, len(inhale_s) + 1), inhale_s, "o", ms=3, color="#1f5f7a", label="Inhale")
b.plot(np.arange(1, len(exhale_s) + 1), exhale_s, "s", ms=3, color="#7a4a1f", label="Exhale")
b.axhline(R.INHALE_S, color="#1f5f7a", lw=0.8, ls="--"); b.axhline(R.EXHALE_S, color="#7a4a1f", lw=0.8, ls="--")
b.set_ylim(3, 7); b.set_xlabel("Breath number (1 to 60)"); b.set_ylabel("Phase length (s)")
b.set_title("Every breath: phase lengths measured from the video", loc="left", fontsize=11)
b.legend(frameon=False, ncol=2, loc="center right")
fig.tight_layout(); fig.savefig(base + "_timing_check.png", dpi=150)
