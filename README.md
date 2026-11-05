# resolve-music-edit

**An AI-agent skill that turns a folder of raw clips and a song into a beat-synced, high-production music edit in DaVinci Resolve.**

Give your coding agent a folder of phone footage and a track. It analyzes every clip, maps the song's beats and
drops, and asks you a few creative questions. Then it builds a real, editable Resolve timeline:

- **Beats:** every cut lands on a detected beat, and the drop lands on your strongest shot.
- **Transitions:** native Fusion transitions such as Crash Zoom, Tunnel of Light, Glitch, RGB Splitter, Warp and Slice Push.
- **Keyframed motion with real motion blur on every shot:** zoom pulses on the beat, zoom-throughs, whips, handheld shake,
  and **Inception-style circular transitions** (barrel roll, vortex twist, mirror-fold "folding city").
- **Speed:** speed changes on whip and burst shots, and an optical-flow slow-mo finale.
- **Look:** a CDL grade with per-clip exposure matching, halation, light leaks and flash hits timed to the music, film grain and a vignette.
- **Titles:** glitch-animated opening and end cards (for example a place and date, then *Shot on iPhone 13 Pro*).
- **Delivery:** a ProRes master plus loudness-safe H.264 mp4s for Reels, TikTok and Shorts.

It was built while editing a 48-clip night walk through Dhaka into a 40-second vertical reel. Every cut was
frame-accurate, and every effect was checked in rendered frames. The API traps found along the way are written
down in [`references/gotchas.md`](references/gotchas.md), so your agent doesn't hit them again.

## Requirements

| | |
|---|---|
| **DaVinci Resolve Studio 21.2+** | The free edition has no external scripting. 21.2 added the clip-effect API this uses. Set *Preferences > System > General > External scripting using* to **Local**. |
| Python 3.9+ | `pip install -r requirements.txt` (numpy, librosa, pillow) |
| ffmpeg + ffprobe | on your `PATH` |
| Fonts | [Noto Sans](https://fonts.google.com/noto/specimen/Noto+Sans) for the reference look (falls back to system fonts) |
| An agent | one that can run shell commands, edit files and ideally view images (Claude Code, Codex CLI, Gemini CLI, Cursor, OpenCode, …) |

It has been tested on Linux with Resolve Studio 21.2. The scripts find Resolve's scripting API on macOS and Windows
too. Those paths follow Blackmagic's documented defaults but haven't been tested yet, so reports and PRs are welcome.

## Install

**Claude Code** (and other agents that load `SKILL.md` skills):
```sh
git clone https://github.com/DhrubaDC1/resolve-music-edit ~/.claude/skills/resolve-music-edit
pip install -r ~/.claude/skills/resolve-music-edit/requirements.txt
```
Then, in a folder of clips: `/resolve-music-edit`, or just *"edit these videos to music"*.
For other agents that support the `SKILL.md` format, clone into that agent's skills folder instead.

**Any other agent:** clone it anywhere and point the agent at the instructions:
```sh
git clone https://github.com/DhrubaDC1/resolve-music-edit ~/tools/resolve-music-edit
```
> Read ~/tools/resolve-music-edit/AGENTS.md and follow it to edit the videos in this folder to ./music/track.mp3

You can also copy or symlink `AGENTS.md` into your project, since many agents load it automatically.

## How a session goes

1. **Survey:** `analyze_clips.py` makes contact sheets and scores each clip for sharpness, motion and brightness. The agent looks at them and describes every clip.
2. **Questions:** music, format and length, vibe, FX intensity, how many Inception transitions, title text, hero shots and look.
3. **Music:** `beats.py` finds the tempo, beats, downbeats and drop candidates. The agent picks the window (build, drop, ending).
4. **Plan:** the agent writes `edit.json` with the shot order, roles and style, and `plan.py` locks every cut to a beat.
5. **Assets:** `fx_assets.py` renders the titles, light leaks, grain and vignette as overlay clips.
6. **Build:** `build.py` creates a new Resolve timeline with the cut, speed, transitions, motion comps, grade and overlay tracks.
7. **Review:** `render_range.py` renders a preview and `review.py` makes contact sheets and strips around each cut, which the agent inspects before showing you.
8. **Deliver**, when you say so: a ProRes master, then `deliver.py` makes H.264 mp4s at about −10 LUFS with a true peak under −0.5 dBTP.

Every script runs standalone and documents its arguments in its docstring, so you can also drive the pipeline by hand. See [`examples/edit.example.json`](examples/edit.example.json) for a complete config.

## Knobs (in `edit.json`)

- `style.fx_level`: `maximal` | `bold` | `subtle`
- `style.inception`: `none` | `some` (on hero shots) | `heavy`
- `style.seed`: a different seed gives a different but equally valid transition mix
- `cuts`: override any cut, e.g. `"17": "vortex"`, `"23": ["T", "Tunnel of Light", 10]`
- `speed`, `grade` (CDL plus presets in SKILL.md), `titles`, `overlays`

## Limitations

- OpenFX parameters (Halation, Glow…) can't be set from scripts, so they run at their defaults. Fusion effects are fully keyframed.
- The agent reviews renders through contact sheets and frame strips. It can't listen to the audio, so watch the result yourself.
- The music must be yours to use. The skill never generates or downloads audio on its own.

## License

MIT. Fonts and music are not included and keep their own licences.
