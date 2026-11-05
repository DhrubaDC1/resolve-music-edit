"""fx_assets.py WORK_DIR [--titles-only]

Overlay clips (all on black -> composite Screen; grain is mid-grey -> Overlay; vignette -> Multiply),
written to <project_dir>/fx/<tag>_{titles,leaks,grain,vignette}.mov (tag = slug of timeline_name, so a
re-run never overwrites media Resolve already has cached). Timed on WORK/plan.json's beat grid.

edit.json "titles":
  {"open":  [{"text": "DHAKA", "font": "display", "size": 320, "y": 0.50, "color": [255,255,255]},
             {"text": "04.11.2026", "font": "display", "size": 66, "y": 0.60, "color": [255,200,120], "tracking": 22}],
   "open_bars": 2,
   "over_finale": [],                       # optional lines over the finale shot
   "end":   [{"text": "Shot on", "font": "light", "size": 62, "y": 0.47},
             {"text": "iPhone 13 Pro", "font": "semibold", "size": 104, "y": 0.53}]}
  size = px on a 1080-px short side; y = fraction of frame height (text centre); fonts: display | light |
  semibold | bold | regular | bengali | /path/to/font.ttf  (see FONTS below)
edit.json "overlays": {"leaks": true, "grain": 45, "vignette": true}
"""
import json, subprocess, sys, os, re, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W_ = sys.argv[1]; ONLY_TITLES = "--titles-only" in sys.argv
cfg = json.load(open(f"{W_}/edit.json")); plan = json.load(open(f"{W_}/plan.json"))
N, B, FPS = plan["end_frame"], plan["beat_frames"], plan["fps"]
portrait = cfg.get("height", 3840) > cfg.get("width", 2160)
W, H = (1080, 1920) if portrait else (1920, 1080)
OUT = os.path.join(cfg["project_dir"], "fx"); os.makedirs(OUT, exist_ok=True)
TAG = re.sub(r"[^A-Za-z0-9]+", "_", cfg["timeline_name"]).strip("_")
# Font roles -> preferred files, searched in the OS font folders (first hit wins). Noto Sans (free, Google
# Fonts) gives the reference look; the fallbacks keep it working on a stock macOS / Windows / Linux box.
FONTS = {
    "display":  ["NotoSans-ExtraCondensedBlack.ttf", "Anton-Regular.ttf", "BebasNeue-Regular.ttf", "Impact.ttf",
                 "impact.ttf", "ariblk.ttf", "Arial Black.ttf", "DejaVuSansCondensed-Bold.ttf"],
    "light":    ["NotoSans-Light.ttf", "Inter-Light.ttf", "segoeuil.ttf", "HelveticaNeue.ttc", "Arial.ttf", "arial.ttf",
                 "DejaVuSans-ExtraLight.ttf", "DejaVuSans.ttf"],
    "regular":  ["NotoSans-Regular.ttf", "Inter-Regular.ttf", "segoeui.ttf", "Arial.ttf", "arial.ttf", "DejaVuSans.ttf"],
    "semibold": ["NotoSans-SemiBold.ttf", "Inter-SemiBold.ttf", "seguisb.ttf", "Arial Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "bold":     ["NotoSans-Bold.ttf", "Inter-Bold.ttf", "segoeuib.ttf", "Arial Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "bengali":  ["NotoSansBengali-ExtraCondensedBlack.ttf", "NotoSansBengali-Black.ttf", "NotoSansBengali-Bold.ttf",
                 "Vrinda.ttf", "vrinda.ttf", "Bangla Sangam MN.ttc"],
}
FONT_DIRS = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.local/share/fonts"),
             os.path.expanduser("~/.fonts"), "/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts"),
             os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts")]
_index = None
def _font_index():
    global _index
    if _index is None:
        _index = {}
        for root in FONT_DIRS:
            if os.path.isdir(root):
                for dp, _, fs in os.walk(root):
                    for f in fs: _index.setdefault(f, os.path.join(dp, f))
    return _index

def font(name, size):
    if os.path.isabs(name):
        assert os.path.exists(name), f"font missing: {name}"
        return ImageFont.truetype(name, size)
    for cand in FONTS[name]:
        if cand in _font_index(): return ImageFont.truetype(_font_index()[cand], size)
    raise SystemExit(f"no font found for role {name!r} (tried {FONTS[name]}). Install Noto Sans "
                     "(https://fonts.google.com/noto/specimen/Noto+Sans) or give an absolute .ttf path in edit.json.")

def writer(path, w, h, prof):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS),
                             "-i", "-", "-c:v", "prores_ks", "-profile:v", prof, "-pix_fmt", "yuv422p10le", path], stdin=subprocess.PIPE)

def layer(lines):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for ln in lines:
        f = font(ln.get("font", "display"), int(ln["size"])); yc = ln["y"] * H
        col = tuple(ln.get("color", (255, 255, 255))); tr = ln.get("tracking", 0); txt = ln["text"]
        if tr:
            ws = [d.textlength(c, font=f) for c in txt]; x = (W - sum(ws) - tr * (len(txt) - 1)) / 2
            for c, cw in zip(txt, ws): d.text((x, yc), c, font=f, fill=col, anchor="lm"); x += cw + tr
        else:
            d.text((W / 2, yc), txt, font=f, fill=col, anchor="mm")
    a = np.asarray(im, np.float32) / 255
    return np.clip(a + np.asarray(im.filter(ImageFilter.GaussianBlur(28)), np.float32) / 255 * 1.4, 0, 1)

def glitch(img, amt, seed):
    if amt <= 0.01: return img
    r = np.random.default_rng(seed); out = img.copy(); dx = int(6 + 40 * amt)
    out[..., 0] = np.roll(img[..., 0], dx, axis=1); out[..., 2] = np.roll(img[..., 2], -dx, axis=1)
    for _ in range(int(3 + 12 * amt)):
        y = r.integers(0, H - 40); hh = r.integers(8, int(30 + 140 * amt))
        out[y:y + hh] = np.roll(out[y:y + hh], r.integers(-int(160 * amt) - 1, int(160 * amt) + 1), axis=1)
    if amt > 0.6 and r.random() < 0.5: out = out * (0.4 + 0.6 * r.random())
    return out

def hit(f, hits, n=6):
    return max([1 - (f - h) / n for h in hits if 0 <= f - h < n] or [0.0])

T = cfg.get("titles", {})
op = layer(T["open"]) if T.get("open") else None
fin = layer(T["over_finale"]) if T.get("over_finale") else None
end = layer(T["end"]) if T.get("end") else None
ob = B[min(len(B) - 1, 4 * T.get("open_bars", 2))]
FIN, CEND = plan["shots"][-1]["rec_start"], plan["shots"][-1]["rec_end"]
titles = f"{OUT}/{TAG}_titles.mov"
p = writer(titles, W, H, "3"); black = np.zeros((H, W, 3), np.float32)
for f in range(N):
    img = black
    if op is not None and f < ob:
        img = glitch(op, max(hit(f, [0], 8), hit(f, [x for x in B if x < ob][4:5], 5) * .7,
                             hit(f, [x for x in B if 0 < x < ob], 3) * .4, 1.0 if f >= ob - 5 else 0), f)
    elif fin is not None and FIN <= f < CEND:
        img = glitch(fin * .9, max(hit(f, [FIN], 8), hit(f, [x for x in B if x > FIN], 3) * .4), f)
    elif end is not None and f >= CEND:
        img = glitch(end, hit(f, [CEND], 6), f)
    p.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
p.stdin.close(); assert p.wait() == 0
print("titles ->", titles)
if ONLY_TITLES: sys.exit(0)

O = cfg.get("overlays", {"leaks": True, "grain": 45, "vignette": True})
rng = np.random.default_rng(7)
if O.get("leaks", True):
    LW, LH = W // 2, H // 2
    yy, xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
    heroes = [s["rec_start"] for s in plan["shots"] if s["role"] in ("hero", "finale")]
    dr = plan["drop_frame"]
    hits = [(dr, 1.0, 5, (1.0, .95, .85), True)]
    hits += [(h, .85, 10, (1.0, .45, .1), False) for h in heroes if h != dr]
    hits += [(x, .45, 8, (1.0, .2, .55), False) for x in B[::8] if x not in heroes and x != dr]
    hits += [(x, .6, 3, (1, 1, 1), True) for x in B if B[-1] - 16 <= x < FIN and B.index(x) % 2 == 0]
    blobs = {h[0]: (rng.uniform(.1, .9) * LW, rng.uniform(.15, .85) * LH, rng.uniform(-3, 3), rng.uniform(-4, 4)) for h in hits}
    p = writer(f"{OUT}/{TAG}_leaks.mov", LW, LH, "0")
    for f in range(N):
        img = np.zeros((LH, LW, 3), np.float32)
        for h, s, dec, col, full in hits:
            t = f - h
            if t < -1 or t > dec * 5: continue
            e = s * (.5 if t == -1 else np.exp(-max(t, 0) / dec))
            if full: img += e * np.array(col)
            else:
                cx, cy, vx, vy = blobs[h]; cx += vx * t; cy += vy * t
                g = np.exp(-(((xx - cx) / (LW * .55)) ** 2 + ((yy - cy) / (LH * .35)) ** 2))
                img += e * g[..., None] * np.array(col)
        p.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close(); assert p.wait() == 0; print("leaks ->", f"{OUT}/{TAG}_leaks.mov", len(hits), "hits")
if O.get("grain", 45):
    gw, gh = (720, 1280) if portrait else (1280, 720)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x808080:s={gw}x{gh}:r={FPS}:d={N / FPS}",
                    "-vf", "noise=alls=38:allf=t+u,gblur=sigma=0.6,format=yuv422p10le", "-frames:v", str(N),
                    "-c:v", "prores_ks", "-profile:v", "0", f"{OUT}/{TAG}_grain.mov"], check=True)
    print("grain ->", f"{OUT}/{TAG}_grain.mov")
if O.get("vignette", True):
    vy, vx = np.mgrid[0:H, 0:W].astype(np.float32)
    rr = np.sqrt(((vx - W / 2) / (W * .62)) ** 2 + ((vy - H / 2) / (H * .62)) ** 2)
    v = np.clip(1 - .75 * np.clip(rr - .45, 0, 1) ** 1.6 / .55 ** 1.6, .25, 1)
    png = f"{OUT}/{TAG}_vignette.png"
    Image.fromarray((np.repeat(v[..., None], 3, 2) * 255).astype(np.uint8)).save(png)
    # a still imports as a 5 s clip; a full-length mov does not
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", png, "-frames:v", str(N), "-r", str(FPS),
                    "-c:v", "prores_ks", "-profile:v", "0", "-pix_fmt", "yuv422p10le", f"{OUT}/{TAG}_vignette.mov"], check=True)
    print("vignette ->", f"{OUT}/{TAG}_vignette.mov")
