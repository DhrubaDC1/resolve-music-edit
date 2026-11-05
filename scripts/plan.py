"""plan.py WORK_DIR  ->  WORK/plan.json

Reads WORK/edit.json, WORK/beats.json, WORK/clips.json. Every cut lands on a detected beat.
edit.json essentials:
  "fps": 24,
  "music": {"path": ".../track.mp3", "in": 49.667, "drop": 60.883, "final": 88.073, "bass_end": 89.7, "out": 90.4},
  "build":  [["C064", 4, "wide"], ...],     # music.in -> drop ; beats per shot must sum exactly
  "drop":   [["C090", 4, "hero"], ...],     # drop -> final
  "finale": "C064"                          # final hit -> bass_end, then black until out
Clip refs may be any unique substring of a file stem. Roles: wide, hero, "", burst, whip (finale is automatic).
A clip may repeat: the second use picks a different moment (no overlap, >= 1 s apart).
"""
import sys, json, numpy as np

W = sys.argv[1]
cfg = json.load(open(f"{W}/edit.json")); beats = np.array(json.load(open(f"{W}/beats.json"))["beats"])
clips = json.load(open(f"{W}/clips.json")); FPS = cfg.get("fps", 24); m = cfg["music"]

def ref(k):
    hit = [s for s in clips if k in s]
    assert len(hit) == 1, f"clip ref {k!r} matches {hit}"
    return hit[0]

bi = lambda x: int(np.argmin(np.abs(beats - x)))
b0, bd, bf = bi(m["in"]), bi(m["drop"]), bi(m["final"])
nb = sum(n for _, n, _ in cfg["build"]); nd = sum(n for _, n, _ in cfg["drop"])
assert nb == bd - b0, f"build has {nb} beats, music has {bd - b0} between in and drop"
assert nd == bf - bd, f"drop has {nd} beats, music has {bf - bd} between drop and final"
tl = lambda x: int(round((x - m["in"]) * FPS))
used = {}

def pick(stem, dur, role):
    c = clips[stem]; sr = c["sample_rate"]
    n_src = int(c["n"] / sr * c["fps"])
    sharp, motion = np.array(c["sharp"]), np.array(c["motion"])
    lo, hi = 6, n_src - dur - 6
    assert hi >= lo, f"{stem} ({n_src} frames) too short for a {dur}-frame shot"
    best, bs = None, -1e18
    for s in range(lo, hi + 1, 2):
        a = int(s * sr / c["fps"]); e = max(a + 1, int((s + dur) * sr / c["fps"]))
        v = np.median(sharp[a:e])
        if role == "whip": v = motion[a:e].mean() * 100          # whips want the motion blur
        if any(s < p + pd + 24 and p < s + dur + 24 for p, pd in used.get(stem, [])): v -= 1e9
        if v > bs: bs, best = v, s
    assert bs > -1e8, f"{stem}: no unused window left for reuse"
    used.setdefault(stem, []).append((best, dur))
    return best

shots, k = [], b0
for sec, lst in (("build", cfg["build"]), ("drop", cfg["drop"])):
    for key, n, role in lst:
        stem = ref(key); r0 = 0 if k == b0 else tl(beats[k]); r1 = tl(beats[k + n])
        s = pick(stem, r1 - r0, role)
        shots.append(dict(clip=stem, file=clips[stem]["file"], role=role, beats=n, rec_start=r0, rec_end=r1,
                          src_start=s, src_end=s + r1 - r0, section=sec))
        k += n
stem = ref(cfg["finale"]); r0, r1 = tl(beats[bf]), tl(m["bass_end"])
s = pick(stem, r1 - r0, "wide")
shots.append(dict(clip=stem, file=clips[stem]["file"], role="finale", beats=0, rec_start=r0, rec_end=r1,
                  src_start=s, src_end=s + r1 - r0, section="finale"))
for a, b in zip(shots, shots[1:]): assert a["rec_end"] == b["rec_start"], "gap/overlap"
plan = dict(music_in=m["in"], music_out=m["out"], drop_frame=tl(m["drop"]), end_frame=tl(m["out"]),
            beat_frames=[tl(x) for x in beats[b0:] if x <= m["out"]], fps=FPS, shots=shots)
json.dump(plan, open(f"{W}/plan.json", "w"), indent=1)
print(f"{len(shots)} shots | drop at frame {plan['drop_frame']} | end {plan['end_frame']} ({plan['end_frame'] / FPS:.2f}s)")
for i, x in enumerate(shots):
    print(f"{i:3d} {x['rec_start']:5d}-{x['rec_end']:5d} ({x['rec_end'] - x['rec_start']:3d}f) {x['clip'][-38:]:38s} src {x['src_start']:5d} {x['role']}")
