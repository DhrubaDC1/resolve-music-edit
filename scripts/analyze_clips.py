"""analyze_clips.py VIDEO_DIR WORK_DIR

For every video in VIDEO_DIR (non-recursive):
  * probe size / rotation / fps / duration
  * a 2x2 contact sheet (4 evenly spaced frames)          -> WORK/sheets/<stem>.jpg
  * group sheets of 4 clips, labelled, for quick viewing    -> WORK/groups/group_NN.jpg
  * sharpness / motion / brightness at 6 samples per second -> WORK/clips.json
Clip key = the file stem. Prints a one-line summary per clip.
"""
import sys, os, json, subprocess, glob, numpy as np
from PIL import Image, ImageDraw, ImageFont

VID, WORK = sys.argv[1], sys.argv[2]
EXT = (".mov", ".mp4", ".m4v", ".mkv", ".mxf", ".avi", ".MOV", ".MP4")
os.makedirs(f"{WORK}/sheets", exist_ok=True); os.makedirs(f"{WORK}/groups", exist_ok=True)
files = sorted(f for f in glob.glob(os.path.join(VID, "*")) if f.endswith(EXT))
assert files, f"no videos in {VID}"

def probe(f):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,r_frame_rate:stream_side_data=rotation:format=duration", "-of", "json", f],
        capture_output=True, text=True).stdout)
    s = j["streams"][0]; rot = 0
    for sd in s.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    w, h = s["width"], s["height"]
    if abs(rot) in (90, 270): w, h = h, w            # displayed orientation
    n, dnm = map(int, s["r_frame_rate"].split("/"))
    return dict(width=w, height=h, rotation=rot, fps=round(n / dnm, 3), duration=float(j["format"]["duration"]))

SW, SH, SR = 135, 240, 6
out = {}
for f in files:
    stem = os.path.splitext(os.path.basename(f))[0]
    info = probe(f)
    portrait = info["height"] > info["width"]
    tw, th = (240, 427) if portrait else (427, 240)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-vf",
                    f"fps=4/{info['duration']:.3f},scale={tw}:{th},tile=2x2", "-frames:v", "1",
                    f"{WORK}/sheets/{stem}.jpg"], check=True, stdin=subprocess.DEVNULL)
    sw, sh = (SW, SH) if portrait else (SH, SW)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-vf", f"fps={SR},scale={sw}:{sh}", "-pix_fmt", "gray",
                          "-f", "rawvideo", "-"], capture_output=True, stdin=subprocess.DEVNULL).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw).astype(np.float32)
    lap = fr[:, 1:-1, 1:-1] * 4 - fr[:, :-2, 1:-1] - fr[:, 2:, 1:-1] - fr[:, 1:-1, :-2] - fr[:, 1:-1, 2:]
    sharp = lap.var(axis=(1, 2)); motion = np.r_[0, np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))]
    bright = fr.mean(axis=(1, 2))
    out[stem] = dict(file=os.path.abspath(f), n=len(fr), sample_rate=SR, **info,
                     sharp=sharp.round(1).tolist(), motion=motion.round(2).tolist(), bright=bright.round(1).tolist())
    print(f"{stem:45s} {info['width']}x{info['height']} rot{info['rotation']:>4} {info['fps']}fps {info['duration']:6.2f}s "
          f"sharp {np.median(sharp):7.1f} motion {np.median(motion):5.2f} bright {bright.mean():5.1f}", flush=True)

json.dump(out, open(f"{WORK}/clips.json", "w"))
# labelled groups of 4 sheets
font = ImageFont.load_default(size=22) if hasattr(ImageFont, "load_default") else None
stems = list(out)
for g in range(0, len(stems), 4):
    ims = [Image.open(f"{WORK}/sheets/{s}.jpg") for s in stems[g:g + 4]]
    w, h = ims[0].size
    canvas = Image.new("RGB", (w * 2 + 8, (h + 30) * 2 + 8), (20, 20, 20)); d = ImageDraw.Draw(canvas)
    for k, (im, s) in enumerate(zip(ims, stems[g:g + 4])):
        x, y = (k % 2) * (w + 8), (k // 2) * (h + 38)
        d.text((x + 4, y + 2), s[-40:], fill=(255, 220, 0), font=font)
        canvas.paste(im.resize((w, h)), (x, y + 30))
    canvas.save(f"{WORK}/groups/group_{g // 4:02d}.jpg", quality=85)
print(f"{len(out)} clips -> {WORK}/clips.json ; {len(range(0, len(stems), 4))} group sheets in {WORK}/groups/")
