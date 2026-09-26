# 4:6 paced-breathing pacer: working examples

Everything here implements one specification: 6 breaths per minute (0.1 Hz), inhale 4.0 s, exhale 6.0 s, no pauses, raised-cosine easing within each phase, 60 breaths (10:00) of silent pacing after a 60-s instruction section and three labelled practice breaths.

## What's in the folder

| File | What it is |
|---|---|
| `videos/pacer_circle_4-6_full_session_silent.mp4` | **The recommended stimulus as a full example.** 11:45 total: instructions (0:00–1:00), practice (1:00–1:30), 10:00 silent pacing (1:30–11:30), end (11:30–11:45). One soft chime when pacing ends. Captions, no voice yet. 5.1 MB. |
| `videos/pacer_circle_4-6_full_session_phase-tones.mp4` | Identical video with soft tones at each in-breath and out-breath onset, so you can hear the alternative. Not recommended for the study. |
| `videos/preview_<style>_4-6_60s.mp4` | 60-s previews of five visual designs (circle, ball, bar, water, ring). Three labelled breaths, then three unlabelled. No audio track. |
| `videos/..._timing_check.png` and `.csv` | Frame-by-frame measurement of the circle in the full-session MP4 against the timing model. |
| `pacer_gallery.html` | Interactive comparison of the five designs, running in sync from one clock, with a live waveform trace. Open in any browser. |
| `qualtrics/option-A_video/` | HTML and JavaScript for embedding the MP4 in Qualtrics with gating, seek blocking, pause-on-tab-switch, and logging. |
| `qualtrics/option-B_live-pacer/` | HTML and JavaScript for a live, clock-driven pacer drawn in Qualtrics. No video hosting needed. |
| `instruction_script.md` | Timed voiceover script matching the on-screen cards, with delivery notes. |
| `render_pacer.py` | Generates all the videos from the parameters at the top of the file. |
| `verify_timing.py` | Decodes a rendered MP4 and checks its timing. |
| `tests/harness.py` | Runs either Qualtrics option headless with a mocked `Qualtrics.SurveyEngine`. |

## Verification (full-session silent MP4)

Decoded frame by frame, measuring the circle's diameter on the centre row:

- 21,150 frames at 30 fps, 705.000 s, exactly as specified.
- Across all 60 pacing breaths, cycle period 10.000 s (range 9.9997–10.0005), which is 6.000 breaths per minute.
- Inhale measured at 4.01 s and exhale at 6.01 s for every breath. The 0.01 s is the measurement's interpolation between frames, not the video.
- Circle size matches the model to within 0.6 px at every frame (mean error −0.06 px).
- Tone onsets in the tones version are spaced exactly 4.0 s and 6.0 s apart.

Re-run it after any change: `python3 verify_timing.py out/<file>.mp4`.

## Adding Andrew's voiceover

Record the script in `instruction_script.md` as one mono WAV, starting at 0:00, then mix it with the existing track (which holds the end chime) without re-encoding the picture:

```
ffmpeg -i out/pacer_circle_4-6_full_session_silent.mp4 -i voice.wav \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 64k -ac 1 -movflags +faststart \
  pacer_circle_4-6_final.mp4
```

Re-run `verify_timing.py` on the result. The picture is copied untouched, so timing can't change, but it's a cheap check to report.

If you'd rather not have any audio, keep captions only and strip the track (`-an`). A video with no audio track can autoplay in every major browser, which removes one failure point.

## Qualtrics setup

Both options need the account permissions "Allow JavaScript" and "Allow all HTML markup."

1. Add a Text/Graphic question on its own page. Paste `question.html` into its HTML View and `question.js` into its JavaScript editor.
2. For option A, host the MP4 somewhere that serves it directly (an ETH or Stanford web server, or the Qualtrics file library, since it's under the 16 MB limit) and set `CONFIG.videoUrl`.
3. In Survey Flow, add an Embedded Data element **above** the block with every field listed at the top of `question.js`. In the new survey-taking experience, name them with the `__js_` prefix (`__js_spb_completed`, and so on). In the legacy experience, drop the prefix. The script writes both ways.
4. Screen out phones in Survey Flow as well; the script also refuses viewports under 800 px wide.
5. Preview on Chrome, Safari, Firefox, and Edge. Switch tabs mid-exercise once and confirm the Continue prompt appears and `hidden_n` is recorded.

What each option logs is documented in its `question.js`. The key compliance fields are `completed`, `hidden_n`/`hidden_s` (tab switches), and `wall_s` against the expected duration.

Both were tested in headless Chromium with a mocked SurveyEngine (`tests/harness.py`). Option A started playback from the button with sound allowed, snapped back a skip-ahead attempt, paused and logged a simulated tab switch, counted 60.0 of 60.0 s watched on a test clip, and only then revealed Next. Option B delivered exactly 630.0 s of pacer time, kept Next hidden throughout, paused and logged a simulated tab switch, and revealed Next at the end. Real Qualtrics may differ in details, so step 5 isn't optional.

## Changing the protocol

All parameters sit at the top of `render_pacer.py` and in `CONFIG` in option B.

- **5:5 or another ratio:** set `INHALE_S` and `EXHALE_S`. Each must be a whole number of frames at 30 fps (multiples of 1/30 s).
- **2 × 5 minutes with a 1-minute break** (the You et al. 2021 structure, if 10 continuous minutes proves too demanding in piloting): build the sequence in `build_full()` as 30 plain cycles, a held rest segment, then 30 more.
- **A different design:** call `build_full("ball")` or any other style name.

## Licensing and credit

The font is Atkinson Hyperlegible (SIL Open Font License), chosen for legibility of on-screen text. Everything else was generated here and is yours to license. A reasonable choice is CC BY 4.0 for the videos and MIT for the code when you post them to OSF with the paper. Decide authorship credit for the stimulus before posting.
