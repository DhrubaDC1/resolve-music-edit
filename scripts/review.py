"""review.py RENDER.mov WORK_DIR [cut_index ...]

WORK/review/overview.jpg  every 6th frame of the render (read it to judge pacing, grade, titles)
WORK/review/cuts.jpg      16-frame strips (7 before .. 8 after) around the given incoming-shot indices
                          (default: the drop, every hero shot and the finale)
WORK/review/cutcheck.txt  planned cuts vs detected scene changes (dark-to-dark cuts may not register)
"""
import sys, os, json, subprocess, re

V, W = sys.argv[1], sys.argv[2]; os.makedirs(f"{W}/review", exist_ok=True)
plan = json.load(open(f"{W}/plan.json")); sh = plan["shots"]
st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                               "-of", "json", V], capture_output=True, text=True).stdout)["streams"][0]
w, h = st["width"], st["height"]
tw, th = (96, 170) if h > w else (170, 96)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", V, "-vf", f"select='not(mod(n\\,6))',scale={tw}:{th},tile=14x12",
                "-fps_mode", "vfr", "-frames:v", "1", f"{W}/review/overview.jpg"], check=True)
idx = [int(x) for x in sys.argv[3:]] or sorted({next(i for i, s in enumerate(sh) if s["section"] == "drop")} |
                                              {i for i, s in enumerate(sh) if s["role"] in ("hero", "finale")})
strips = []
for k, i in enumerate(idx):
    c = sh[i]["rec_start"]; out = f"{W}/review/_strip{k}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", V, "-vf",
                    f"select='between(n\\,{c - 7}\\,{c + 8})',scale={tw + 24}:{th + 43},tile=16x1",
                    "-fps_mode", "vfr", "-frames:v", "1", out], check=True)
    strips.append(out)
args = sum([["-i", s] for s in strips], [])
subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", f"vstack={len(strips)}" if len(strips) > 1 else "null",
                f"{W}/review/cuts.jpg"], check=True)
for s in strips: os.remove(s)
log = subprocess.run(["ffmpeg", "-hide_banner", "-i", V, "-vf", "scale=270:-2,select='gt(scene,0.2)',showinfo", "-an", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
sc = [round(float(x) * plan["fps"]) for x in re.findall(r"pts_time:([0-9.]+)", log)]
nfr = int(json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
          "stream=nb_read_packets", "-of", "json", V], capture_output=True, text=True).stdout)["streams"][0]["nb_read_packets"])
cuts = [s["rec_start"] for s in sh[1:] if s["rec_start"] < nfr]   # only meaningful on a render WITHOUT transitions
exact = [c for c in cuts if c in sc]; near = [c for c in cuts if any(abs(c - x) <= 1 for x in sc)]
txt = f"planned cuts {len(cuts)} | exact {len(exact)} | within 1f {len(near)} | not detected {[c for c in cuts if c not in near]}"
open(f"{W}/review/cutcheck.txt", "w").write(txt + "\n"); print(txt)
print("strips for shots", idx, "->", f"{W}/review/cuts.jpg ; overview -> {W}/review/overview.jpg")
