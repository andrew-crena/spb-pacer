# Voice-recording and final-video production guide

## 1. Recording a budget Pyle dynamic mic

A cheap dynamic mic can sound completely adequate for this use because the final recording is short, mono, and mostly speech. The room and mic distance matter more than expensive processing.

### Hardware

- If the mic is **XLR**, use a basic USB audio interface or XLR-to-USB interface with a real microphone preamp. Avoid passive XLR-to-3.5 mm adapters.
- Put the mic on a stand rather than holding it.
- Use a foam windscreen or pop filter.
- Record 2–4 in / 5–10 cm from the mic, roughly 20–30 degrees off-axis from the mouth.
- Set gain so ordinary speech peaks around −12 to −6 dBFS and never clips.

### Room

- Choose the smallest quiet room that does not sound boxy.
- Face curtains, clothing, a duvet, or moving blankets rather than a bare wall.
- Turn off fans/HVAC if practical for the one-minute recording.
- Record 10–15 seconds of room tone after the script for editing reference.

## 2. Software

### Fast/free route: Audacity

Record mono, 48 kHz. Use this conservative chain:

1. High-pass filter around 70–90 Hz.
2. Remove only obvious resonances with small EQ cuts.
3. Compressor around 2:1, aiming for 2–4 dB gain reduction on louder phrases.
4. Mild de-esser only if the mic makes S sounds distracting.
5. Avoid aggressive noise reduction unless there is a stable hum/hiss. Too much sounds worse than a small amount of room noise.
6. Loudness normalize the finished voice to about −16 LUFS, with peaks below −1 dBTP.
7. Export mono 48 kHz WAV.

### Better control: REAPER or DaVinci Resolve/Fairlight

Use the same processing concept but automate phrase levels manually before compression. This usually sounds more natural than heavy compression.

## 3. Voice style

- Speak softly, but do not whisper. Whispering makes a dynamic mic noisy because you have to add gain later.
- Keep consonants clear and vowels natural.
- Use an instructional tone rather than a meditation-performance tone.
- Do not add audible breaths for atmosphere.

## 4. Ambience options

### Best scientific default

**No ambience.** Spoken setup, silent pacing, soft end chime.

### If an ambience track is desired

Use one fixed track for all participants and document it. Keep it very low under the voice and pacing. Good development candidates are:

- broad-band pink or brown noise;
- continuous distant surf with no salient gulls/voices;
- steady light rain without thunder;
- neutral room-like environmental texture.

Avoid tracks with obvious musical harmony, rhythmic pulses, birdsong events, thunder, spoken content, or dramatic wave crashes. Those can affect attention, pleasantness, arousal, and expectancy independently of breathing.

### Licensing

Use a self-recorded track, CC0/public-domain material, or a track with an explicit license that permits redistribution inside the study file. Save the license page/PDF with the study materials.

## 5. Final mix

Suggested target relationship:

- Voice: around −16 LUFS integrated for the spoken segment.
- Ambience: roughly 18–30 dB below the voice by ear, depending on the source.
- End chime: audible but not startling; soft attack and decay.

Do not normalize the ambience to the same loudness as the narration.

## 6. Video workflow

1. Lock visual timing first.
2. Record and edit the voice to one mono WAV.
3. Add the voice and optional ambience without re-timing the picture.
4. Export H.264 MP4, AAC audio, `+faststart` for browser delivery.
5. Re-run the frame-level timing verification after the final mux.
6. Test in Qualtrics on Chrome, Safari, Firefox, and Edge.

## 7. Qualtrics

The final participant page should expose no audio controls beyond normal playback if possible. Hide Next until the full stimulus completes, prevent seeking ahead, and log tab switches/completion. If autoplay with sound is unreliable, require one clear Start button.
