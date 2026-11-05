# Measured gotchas (Resolve Studio 21.2.0.5 on Linux unless noted; each one cost real time)

- **AppendToTimeline endFrame is EXCLUSIVE** in the raw API (the MCP tool's end_frame is too). Off-by-one ->
  every clip one frame short. build.py asserts start+duration of every item.
- **Append in batches of ~10.** One 52-clip append coincided with the Wayland compositor (Hyprland) crashing,
  which killed Resolve. Small batches + 0.5 s sleeps have been stable. If Resolve vanishes: check
  `coredumpctl list`, relaunch (MCP resolve_control launch), reload the project — autosave usually kept it.
- **No Inspector keyframes in the API** (TimelineItem.AddKeyframe absent). Animate via a Fusion effect comp
  (fxlib.motion_comp). **Comp frame 0 = the item's first timeline frame.** Fusion effects DO render (verified).
- Fusion splines: build the BezierSpline then connect; Point inputs need an XYPath with X/Y splines.
- **Transform Edges = 3 (mirror)** hides borders on shake/zoom-out/rotation; at large rotations it shows mirrored
  copies — that's the "fold" look, and acceptable under motion blur elsewhere.
- **SetSpeed** works (21.1+) and keeps record duration with RippleTimeline False; source consumed = dur × speed,
  so cap speed by remaining media (build.py does). Slow-mo: also set RetimeProcess = RETIME_OPTICAL_FLOW.
- **AddTransition** needs handles; try alignment center -> left -> right, else fall back to a motion cut.
- **Stills import as 5 s clips** — make vignette etc. full-length movs.
- Changing an overlay: write a NEW file name and swap the clip; overwriting a file Resolve already cached can
  show stale frames. Keep the old timeline untouched for comparison.
- **Render path must be inside a Media Storage volume** ("Render path inaccessible…"); /tmp is not. AddRenderJob
  just returns empty/False otherwise.
- **Linux Resolve has no H.264/H.265 encoder** (mp4 offers only APV). Render ProRes (render_range.py falls back to
  DNxHR where ProRes is missing), then encode with ffmpeg (deliver.py). Same path works on macOS/Windows.
- Stop a render: `p.StopRendering()`; delete the partial file and the job (`DeleteAllRenderJobs`).
- Phone footage carries rotation metadata (e.g. -90); Resolve honours it (timeline shows upright) and
  analyze_clips reports displayed orientation.
- Run scripts with a python3 that has numpy/librosa/pillow (`requirements.txt`); `scripts/resolve_env.py` finds the
  Resolve module itself on Linux/macOS/Windows (a Resolve MCP server's private venv may lack numpy).
- zsh: `$var:l…` is a modifier (`$target_offset:linear` broke an ffmpeg filter) — always `${var}`.
- Club-mastered music arrives ~-6 LUFS and +1.7 dBTP; AAC overshoots a plain limiter. deliver.py uses a 4×
  oversampled limiter at -3 dBFS -> ~-10 LUFS, -0.6 dBTP.
- Default OFX Glow blows out storefront neon; Halation default is good. OFX params can't be set from scripts.
- MCP auto-archives timelines on some destructive calls (`<name>_archived_v01`) — harmless, mention it.
