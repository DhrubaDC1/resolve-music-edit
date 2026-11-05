"""build.py WORK_DIR   (python3; Resolve Studio 21.2+ open on the target project)

Builds a NEW timeline (edit.json "timeline_name"; refuses if it exists) from WORK/plan.json:
beat-locked cut -> speed -> native Fusion transitions -> per-shot Fusion motion (punches, beat pulses, shake,
whips, zoom-throughs, spins and the inception moves roll / vortex / fold) -> CDL grade + exposure match ->
Halation -> overlay tracks V2..V5 (leaks Screen, titles Screen, grain Overlay, vignette Multiply). Saves.
Writes WORK/build_report.json (cut map used, transitions placed, speeds).

edit.json keys used here (all optional except project_dir, video_dir, timeline_name, music.path):
  "width"/"height"/"fps"      timeline format (default 2160x3840 @ 24)
  "style": {"fx_level": "maximal|bold|subtle", "inception": "none|some|heavy", "seed": 3}
  "cuts":  {"12": "zoom", "23": ["T", "Tunnel of Light", 10], ...}   per-incoming-shot overrides
  "speed": {"whip": 200, "burst": 140, "finale": 60}
  "grade": {"slope": [1.06,1.0,0.95], "offset": [-0.025,-0.012,0.006], "power": [1.10,1.06,1.02],
            "saturation": 1.30, "target_brightness": 72, "halation": true}
  "overlays": {"leaks": true, "grain": 45, "vignette": true, "titles": true}
Cut types: cut, punch, zoom, spin, whipL, whipR, roll, vortex, fold, or ["T", <Fusion transition name>, frames].
"""
import sys, json, time, re, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fxlib import resolve, motion_comp, key, timeline_by_name

W_ = sys.argv[1]
cfg = json.load(open(f"{W_}/edit.json")); plan = json.load(open(f"{W_}/plan.json"))
clips = json.load(open(f"{W_}/clips.json"))
shots, BEATS, N, FPS = plan["shots"], plan["beat_frames"], plan["end_frame"], plan["fps"]
NAME = cfg["timeline_name"]; TAG = re.sub(r"[^A-Za-z0-9]+", "_", NAME).strip("_")
style = {"fx_level": "maximal", "inception": "some", "seed": 3, **cfg.get("style", {})}
SPEED = {"whip": 200, "burst": 140, "finale": 60, **cfg.get("speed", {})}
G = {"slope": [1.06, 1.0, 0.95], "offset": [-0.025, -0.012, 0.006], "power": [1.10, 1.06, 1.02],
     "saturation": 1.30, "target_brightness": 72, "halation": True, **cfg.get("grade", {})}
OV = {"leaks": True, "grain": 45, "vignette": True, "titles": True, **cfg.get("overlays", {})}
log = lambda *a: print(*a, flush=True)

# ---------------- cut design ----------------
T = lambda n, d: ("T", n, d)
DROP = next(i for i, s in enumerate(shots) if s["section"] == "drop")
def auto_cuts():
    rng = np.random.default_rng(style["seed"]); inc = style["inception"]; lvl = style["fx_level"]
    P = {"wide": ["zoom", T("Slice Push", 8), "roll" if inc != "none" else "spin", "whipL", T("Cross Dissolve", 8)],
         "": ["whipR", "whipL", T("Glitch", 6), "zoom", T("Slice Push", 6), "punch", T("Warp", 8), T("Drop Warp", 8),
              T("Shash", 6), T("Ripple Warp", 8)],
         "burst": [T("RGB Splitter", 4), T("Block Glitch", 4), "punch", T("Inverse Flash", 4), T("Three Color Flash", 4),
                   T("Glitch", 4)],
         "whip": ["whipL", "whipR"],
         "hero": (["vortex", "fold", "roll", T("Tunnel of Light", 10), T("Crash Zoom", 8)] if inc != "none"
                  else ["spin", T("Tunnel of Light", 10), T("Crash Zoom", 8), "zoom"])}
    if inc == "heavy": P[""] += ["roll", "vortex", "fold"]
    if lvl == "subtle":
        P[""] = ["cut", "cut", "punch", "cut", T("Cross Dissolve", 4)]; P["burst"] = ["cut", "punch"]; P["wide"] = ["cut", T("Cross Dissolve", 10)]
    elif lvl == "bold":
        P[""] = P[""] + ["cut", "punch", "cut"]; P["burst"] = P["burst"] + ["cut", "punch"]
    cuts, recent = {}, []
    for i, s in enumerate(shots[1:], 1):
        if i == DROP: c = "zoom"
        elif s["role"] == "finale": c = ("vortex" if inc != "none" else T("Tunnel of Light", 12))
        else:   # no repeat of the last 3 choices ("cut"/"punch" may repeat)
            pool = P.get(s["role"], P[""])
            nm = lambda o: o[1] if isinstance(o, tuple) else o
            opts = [o for o in pool if nm(o) in ("cut", "punch") or nm(o) not in map(nm, recent[-3:])] or pool
            c = opts[rng.integers(len(opts))]
        cuts[i] = c; recent.append(c)
    return cuts
CUT = auto_cuts()
for k, v in cfg.get("cuts", {}).items():
    CUT[int(k)] = tuple(v) if isinstance(v, list) else v

# ---------------- media ----------------
r, p, _ = resolve()
pm = r.GetProjectManager(); mp = p.GetMediaPool(); root = mp.GetRootFolder()
assert not timeline_by_name(p, NAME), f"timeline {NAME!r} exists; pick a new timeline_name or delete it"
def all_clips(folder):
    out = list(folder.GetClipList() or [])
    for sf in folder.GetSubFolderList() or []: out += all_clips(sf)
    return out
def by_path():
    return {c.GetClipProperty("File Path"): c for c in all_clips(root) if c.GetClipProperty("File Path")}
need = sorted({s["file"] for s in shots} | {os.path.abspath(cfg["music"]["path"])})
have = by_path()
if any(n not in have for n in need):
    mp.SetCurrentFolder(root)
    mp.ImportMedia([n for n in need if n not in have]); have = by_path()
missing = [n for n in need if n not in have]; assert not missing, f"not in media pool: {missing}"

# ---------------- timeline ----------------
mp.SetCurrentFolder(root)
t = mp.CreateEmptyTimeline(NAME); assert t, "CreateEmptyTimeline failed"
p.SetCurrentTimeline(t)
t.SetSetting("useCustomSettings", "1")
for k_, v_ in (("timelineResolutionWidth", cfg.get("width", 2160)), ("timelineResolutionHeight", cfg.get("height", 3840)),
               ("timelineFrameRate", FPS)):
    t.SetSetting(k_, str(v_))
s0 = t.GetStartFrame(); items = []
for k in range(0, len(shots), 10):     # small batches: one huge append once took the desktop session down
    batch = [dict(mediaPoolItem=have[s["file"]], startFrame=s["src_start"], endFrame=s["src_end"],   # endFrame EXCLUSIVE
                  recordFrame=s0 + s["rec_start"], trackIndex=1, mediaType=1) for s in shots[k:k + 10]]
    got = mp.AppendToTimeline(batch); assert got and len(got) == len(batch), (k, got)
    items += got; time.sleep(0.5)
mus = mp.AppendToTimeline([dict(mediaPoolItem=have[os.path.abspath(cfg["music"]["path"])], startFrame=round(plan["music_in"] * FPS),
                                endFrame=round(plan["music_out"] * FPS), recordFrame=s0, trackIndex=1, mediaType=2)])
assert mus, "music append failed"
for it, s in zip(items, shots):
    assert it.GetStart() - s0 == s["rec_start"] and it.GetDuration() == s["rec_end"] - s["rec_start"], (s["clip"], it.GetStart() - s0, it.GetDuration())
log("timeline ok:", len(items), "clips, end frame", t.GetEndFrame() - s0)

# ---------------- speed ----------------
for it, s in zip(items, shots):
    want = SPEED.get(s["role"])
    if not want or want == 100: continue
    c = clips[s["clip"]]; n_src = int(c["n"] / c["sample_rate"] * c["fps"]); dur = s["rec_end"] - s["rec_start"]
    pct = min(want, 100 * (n_src - s["src_start"] - 8) / dur) if want > 100 else want    # stay inside the media
    if pct > 105 or want < 100:
        assert it.SetSpeed({"Percentage": float(round(pct)), "RippleTimeline": False}), s["clip"]
        s["speed"] = round(pct)
        if want < 100: it.SetProperty("RetimeProcess", r.RETIME_OPTICAL_FLOW)
log("speeds:", {i: s["speed"] for i, s in enumerate(shots) if s.get("speed")})

# ---------------- native Fusion transitions ----------------
placed = {}
for i, c in sorted(CUT.items()):
    if not (isinstance(c, tuple) and c[0] == "T"): continue
    for align in ("center", "left", "right"):           # needs handles; fall back, then give up -> punch
        tr = items[i].AddTransition({"type": c[1], "category": "simple" if c[1] == "Cross Dissolve" else "fusion",
                                     "position": "start", "alignment": align, "duration": int(c[2])})
        if tr: placed[i] = [c[1], align, tr.GetDuration()]; break
    else:
        log("transition failed -> punch:", i, c); CUT[i] = "punch"
log("transitions placed:", len(placed))

# ---------------- per-shot motion ----------------
ease = lambda x: 1 - (1 - min(max(x, 0), 1)) ** 3
rng = np.random.default_rng(11)
def motion(i, s):
    d = s["rec_end"] - s["rec_start"]; role = s["role"]
    f = np.arange(-6, d + 6); fc = np.clip(f, 0, d - 1)
    size = 1 + {"wide": .10, "hero": .08, "": .05, "finale": .15}.get(role, 0) * fc / max(d - 1, 1)     # slow push-in
    ang = np.zeros(len(f)); cx = np.full(len(f), .5); cy = np.full(len(f), .5); vx = np.zeros(len(f))
    for j, b in enumerate([b - s["rec_start"] for b in BEATS if s["rec_start"] <= b < s["rec_end"]]):   # beat pulses
        amp = {"hero": .18 if j == 0 else .09, "wide": .035, "": .05 if j else 0, "finale": .06 if j == 0 else 0}.get(role, 0)
        if style["fx_level"] == "subtle": amp *= .5
        size = size * (1 + amp * np.where(f >= b, np.exp(-(f - b) / 2.4), 0))
    if role in ("burst", "whip") or i == DROP:          # handheld shake (decaying on the drop)
        a = .016 if i != DROP else .028; n = len(f)
        dec = np.ones(n) if i != DROP else np.exp(-np.clip(f, 0, None) / 10) + .25
        if style["fx_level"] == "subtle": dec = dec * .4
        cx += a * dec * rng.uniform(-1, 1, n); cy += a * dec * rng.uniform(-1, 1, n)
        ang += 2.2 * dec * rng.uniform(-1, 1, n); size = size * 1.08
    cin = CUT.get(i) if i else None; cout = CUT.get(i + 1)
    hu = lambda n: np.array([ease((x + 1) / (n + 1)) for x in f])     # head curve, already moving on the cut frame
    tail = lambda n: np.clip((f - (d - n)) / n, 0, 1) ** 2
    if cin == "spin": h = hu(6); ang += -30 * (1 - h); size = size * (1 + .9 * (1 - h))
    elif cin == "zoom": size = size * (1 + 1.5 * (1 - hu(5)))
    elif cin == "whipL": cx += .9 * (1 - hu(4))
    elif cin == "whipR": cx -= .9 * (1 - hu(4))
    elif cin == "punch": size = size * (1 + .22 * (1 - hu(5)))
    elif cin == "roll": h = hu(8); ang += -90 * (1 - h); size = size * (1 + 1.2 * (1 - h))
    elif cin == "vortex": h = hu(9); vx += 620 * (1 - h); ang += -45 * (1 - h); size = size * (1 + .35 * (1 - h))
    elif cin == "fold": h = hu(10); size = size * (.38 + .62 * h); ang += -135 * (1 - h)
    if cout == "spin": ang += 30 * tail(5); size = size * (1 + .9 * tail(5))
    elif cout == "zoom": size = size * (1 + 2.2 * tail(4))
    elif cout == "whipL": cx -= .9 * tail(3)
    elif cout == "whipR": cx += .9 * tail(3)
    elif cout == "roll": ang += 90 * tail(6); size = size * (1 + 1.2 * tail(6))
    elif cout == "vortex": vx += 620 * tail(7); ang += 45 * tail(7); size = size * (1 + .35 * tail(7))
    elif cout == "fold": size = size * (1 - .62 * tail(7)); ang += 135 * tail(7)
    return f, size, ang, cx, cy, vx

for i, (it, s) in enumerate(zip(items, shots)):
    f, size, ang, cx, cy, vx = motion(i, s)
    if np.abs(size - 1).max() < 1e-4 and np.abs(ang).max() < 1e-3 and np.abs(cx - .5).max() < 1e-4 and not vx.any():
        continue
    comp, xf, vt = motion_comp(it, vortex=bool(np.abs(vx).max() > 0))
    comp.Lock()
    key(comp, xf, "Size", list(zip(f.tolist(), size.tolist())))
    if np.abs(ang).max() > 1e-3: key(comp, xf, "Angle", list(zip(f.tolist(), ang.tolist())))
    if np.abs(cx - .5).max() > 1e-4 or np.abs(cy - .5).max() > 1e-4:
        key(comp, xf, "Center", list(zip(f.tolist(), zip(cx.tolist(), cy.tolist()))))
    if vt: key(comp, vt, "Angle", list(zip(f.tolist(), vx.tolist())))
    comp.Unlock()
log("motion comps done")

# ---------------- grade ----------------
fmt = lambda v, g=1.0: " ".join(f"{x * g:.3f}" for x in v)
for it, s in zip(items, shots):
    b = float(np.mean(clips[s["clip"]]["bright"]))
    g = min(max((G["target_brightness"] / max(b, 1)) ** .35, .85), 1.35)       # exposure match across clips
    assert it.SetCDL({"NodeIndex": "1", "Slope": fmt(G["slope"], g), "Offset": fmt(G["offset"]),
                      "Power": fmt(G["power"]), "Saturation": f"{G['saturation']:.2f}"}), s["clip"]
    if G["halation"]: it.AddEffect("ofx", "Resolve FX/Resolve FX Film Emulation/Halation")
log("grade done")

# ---------------- overlays ----------------
FXD = os.path.join(cfg["project_dir"], "fx")
want = [("leaks", r.COMPOSITE_SCREEN, 100), ("titles", r.COMPOSITE_SCREEN, 100),
        ("grain", r.COMPOSITE_OVERLAY, OV["grain"] or 0), ("vignette", r.COMPOSITE_MULTIPLY, 100)]
want = [w for w in want if OV.get(w[0]) and os.path.exists(f"{FXD}/{TAG}_{w[0]}.mov")]
if want:
    fxf = next((x for x in root.GetSubFolderList() if x.GetName() == "FX"), None) or mp.AddSubFolder(root, "FX")
    mp.SetCurrentFolder(fxf)
    have = by_path()
    for name, mode, op in want:
        path = f"{FXD}/{TAG}_{name}.mov"
        clip = have.get(path) or mp.ImportMedia([path])[0]
        track = t.GetTrackCount("video") + 1; t.AddTrack("video"); t.SetTrackName("video", track, name.upper())
        ov = mp.AppendToTimeline([dict(mediaPoolItem=clip, startFrame=0, endFrame=N, recordFrame=s0, trackIndex=track, mediaType=1)])
        assert ov, name
        ov[0].SetProperty("CompositeMode", mode); ov[0].SetProperty("Opacity", float(op))
        log(f"overlay {name}: V{track}, {ov[0].GetDuration()} frames")
    mp.SetCurrentFolder(root)
t.SetTrackName("video", 1, "PICTURE")
mus[0].SetFades({"FadeIn": 2, "FadeOut": 0})

json.dump(dict(timeline=NAME, cuts={str(k): (list(v) if isinstance(v, tuple) else v) for k, v in CUT.items()},
               transitions={str(k): v for k, v in placed.items()},
               speeds={str(i): s["speed"] for i, s in enumerate(shots) if s.get("speed")}),
          open(f"{W_}/build_report.json", "w"), indent=1)
assert pm.SaveProject()
log("saved:", NAME)
