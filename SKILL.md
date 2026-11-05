---
name: resolve-music-edit
description: Turn a folder of raw video clips plus a music track into a beat-synced, high-production edit (travel / street / hype / cinematic reel) in DaVinci Resolve Studio. Analyses every clip, maps the song's beats and drops, asks the user creative questions first, then builds a Resolve timeline with every cut on the beat, Fusion transitions, keyframed motion (punches, whips, zoom-throughs, Inception-style barrel rolls / vortex twists / mirror folds), speed ramps, colour grade, halation, glitch titles, light leaks, grain and vignette, and exports social-ready mp4s. Use when asked to edit a folder of videos to music, make a reel / travel / hype / cinematic edit, or "edit these like last time".
license: MIT
---

# Resolve music edit

A folder of clips + one track -> a vertical (or horizontal) edit where every cut sits on a detected beat and the
drop lands on the strongest shot. `$SK` below = the folder containing this file. All scripts are plain
`python3 $SK/scripts/<name>.py`; each has a docstring with its full interface. A per-project `edit.json` in a
WORK folder (any scratch/temp dir you own) drives everything.

Before touching Resolve, read `references/gotchas.md` (measured API behaviour that otherwise costs hours) and,
before designing cuts, `references/effects.md`.

**Works with any coding agent** that can run shell commands, read/write files and — ideally — look at images.
Wherever this says "ask the user", use your structured question tool if you have one, otherwise ask in chat and
wait. Wherever it says "look at", open the image with your image-viewing tool; if you cannot view images, ask the
user to describe the clips (or work from filenames + the numeric scores) and say so.

## 0. Preconditions (check them, don't assume)
- **DaVinci Resolve Studio 21.2 or newer**, running (the free edition has no external scripting; `TimelineItem.AddEffect`
  is new in 21.2). Preferences > System > General > *External scripting using* = **Local**.
- Check the bridge: `python3 $SK/scripts/resolve_env.py` prints the Resolve version and open project.
- `python3 -m pip install -r $SK/requirements.txt` (numpy, librosa, pillow); `ffmpeg` + `ffprobe` on PATH.
- Find Resolve's **Media Storage** locations (Preferences > Storage; with a Resolve MCP server: `media_storage get_volumes`).
  Renders must be written inside one of them. Ask the user if unsure.
- A Resolve project to work in: ask which, or create one (empty projects are safest).

## 1. Survey the footage
```
python3 $SK/scripts/analyze_clips.py <VIDEO_DIR> <WORK>
```
Look at every `WORK/groups/group_NN.jpg` (4 clips per image, 4 frames each). Write yourself one line per clip:
subject, light, motion, sharp/blurry, wide/close, energy. Note orientation from the printed sizes. You may offer to
rename clips descriptively (keep the original name as prefix, write an undo script) — ask first, it changes user files.

## 2. Ask before building — make it *theirs*
Open with what you saw ("48 night clips of a city: traffic, rickshaws, neon signs…"), recommend a default for each
question, and only ask what you can't infer. Two short rounds are fine.
1. **Music** — path to their track (and licence). Never invent or fabricate music; you may suggest royalty-free libraries.
2. **Format & length** — vertical 9:16 30-60 s (default for phone footage) / longer / 16:9.
3. **Vibe** — hype, cinematic-moody, cyberpunk-neon, dreamy… (drives grade + transition palette).
4. **FX intensity** — maximal / bold-but-clean / subtle -> `style.fx_level`.
5. **Inception-style circular transitions** — none / a few on hero shots / heavy -> `style.inception`.
6. **Titles** — opening (place, date, title), end card (e.g. "Shot on <camera>", a handle), language/script.
   Cross-check dates against clip filenames/metadata and point out a mismatch; then use what the user says.
7. **Hero shots / must-include / must-avoid**, people to feature or avoid.
8. **Look** — neon-punchy, teal-orange, warm film, cool cyber, B&W; grain and vignette yes/no.

## 3. Map the music
```
python3 $SK/scripts/beats.py <MUSIC_FILE> <WORK>
```
From the energy map pick the window: `in` = a downbeat that starts a build, `drop` = a big bass jump (listed as
candidates), `final` = a downbeat near the end of that section's energy, `bass_end` = where the bass dies,
`out` ≈ bass_end + 0.7 s for the end card. Edit length ≈ out − in. Use exact downbeat times from the printout.

## 4. Write `WORK/edit.json`, then plan
Template: `$SK/examples/edit.example.json` (every key documented in the script docstrings).
Shot-order craft — this is what makes it look expensive:
- `build` (music.in -> drop): wide / atmospheric shots at 4 beats (one bar) each, then 2-beat shots, then 1-beat
  `burst`s in the last bar, ending on a blurry `whip` shot.
- `drop` (drop -> final): **open on the single strongest, brightest shot (role `hero`)**; mostly 2-beat shots with
  1-beat bursts; a 4-beat `hero` every ~6 shots. Keep the end as strong as the start — reuse a top clip at another
  moment rather than finishing on dark/static/soft shots. Blurry fast clips make great `whip` shots.
- `finale`: a calm, wide shot (slow-mo is automatic). Beat counts must add up exactly (plan.py asserts and tells you).
```
python3 $SK/scripts/plan.py <WORK>
```
Grade presets (CDL slope/offset/power/saturation, before per-clip exposure matching):
neon-punchy `[1.06,1.0,0.95] [-0.025,-0.012,0.006] [1.10,1.06,1.02] 1.30` (default) ·
teal-orange `[1.08,1.0,0.92] [-0.03,-0.005,0.015] [1.10,1.06,1.02] 1.25` · warm film `[1.08,1.02,0.94] [-0.02,-0.01,-0.005] [1.05,1.04,1.02] 1.10` ·
cool cyber `[0.96,1.0,1.10] [-0.02,0.0,0.02] [1.10,1.06,1.02] 1.35` · B&W: saturation 0.
```
python3 $SK/scripts/fx_assets.py <WORK>      # titles, light leaks, grain, vignette -> <project_dir>/fx/<tag>_*.mov
```
Look at a few title frames (ffmpeg `select` + `tile`) before building; nothing may run off the frame edge.

## 5. Build in Resolve
```
python3 $SK/scripts/build.py <WORK>
```
Imports missing media, builds the timeline in small batches, applies speed, transitions, per-shot motion, grade,
halation and overlay tracks, saves the project, writes `WORK/build_report.json`. Every run needs a new
`timeline_name` (it refuses to overwrite) — keep old versions so the user can compare.

## 6. Review before showing anything
```
python3 $SK/scripts/render_range.py "<MEDIA_STORAGE>/<Project> renders" preview_v1 0 <end_frame-1> 1080 1920
python3 $SK/scripts/review.py "<…>/preview_v1.mov" <WORK> [shot indices]
```
Look at `review/overview.jpg` and `review/cuts.jpg`: frozen first frames on motion cuts, black corners, murky or
over-dark grade, weak stretches, clipped/unreadable titles, too much glitch. Fix `edit.json`, rebuild as v2, review
again. Be honest about what you checked: contact sheets are not the same as watching with sound — say so.

## 7. Deliver — only when the user asks
If the user says "don't render yet", don't. Render a master, then encode:
```
python3 $SK/scripts/render_range.py "<MEDIA_STORAGE>/<Project> renders" <Name>_master 0 <end_frame-1> 1080 1920 ProRes422HQ
python3 $SK/scripts/deliver.py "<…>/<Name>_master.mov" "<OUT_DIR>/<Name>_final" 1080x1920 [2160x3840]
```
Long renders: run in the background and tell the user. Text changes later: edit `titles` in edit.json, bump
`timeline_name`'s tag or write a new file with `fx_assets.py <WORK> --titles-only`, then swap the clip on the titles
track (V3) — don't rebuild the whole edit.

## Finish
Report where the files are, what's in the edit (structure, transitions, look), what you verified and how, and what
stayed at defaults (OpenFX parameters cannot be scripted). Offer the next tweaks.
