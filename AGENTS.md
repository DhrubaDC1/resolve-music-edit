# Agent instructions

This repository is an agent skill: **resolve-music-edit**. It turns a folder of video clips and a music track into a
beat-synced, effects-heavy edit in DaVinci Resolve Studio.

When a user asks you to edit their videos to music (a reel, a travel or hype edit, "edit these like that Dhaka
video"), **read [`SKILL.md`](SKILL.md) and follow it step by step**. Before calling Resolve, also read
[`references/gotchas.md`](references/gotchas.md), and [`references/effects.md`](references/effects.md) before
designing the cuts.

Rules that matter most:
- Ask the user the creative questions in SKILL.md step 2 **before** building anything.
- Never fabricate music, licences or dates. If a date disagrees with the clip metadata, say so, then use what the user tells you.
- Renaming or moving the user's files needs their OK. Always write an undo script.
- Review a rendered preview frame by frame before you present it, and say exactly what you checked.
- Don't render or export until the user asks. If they say "don't render yet", don't.
- Scripts live in `scripts/`. Run them with `python3`. Each script's docstring documents its full interface.
