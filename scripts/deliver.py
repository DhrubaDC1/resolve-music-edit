"""deliver.py MASTER.mov OUT_BASENAME [WIDTHxHEIGHT ...]     (default 1080x1920)

Social-ready H.264 + AAC mp4s from the ProRes/DNxHR master, e.g.
    python3 deliver.py master.mov ~/Videos/MyEdit_final 1080x1920 2160x3840
Audio: 4x-oversampled -3.2 dB + brickwall limiter at -3 dBFS -> about -10 LUFS with true peak < -0.5 dBTP.
(Club-mastered tracks often arrive at -6 LUFS / +1.7 dBTP and AAC overshoots a plain limiter.)
Prints integrated loudness and true peak of every output.
"""
import sys, subprocess, os, re

master, base = sys.argv[1], sys.argv[2]
sizes = sys.argv[3:] or ["1080x1920"]
AF = "aresample=192000,volume=-3.2dB,alimiter=limit=0.708:attack=0.5:release=40:level=false,aresample=48000"
for s in sizes:
    w, h = map(int, s.lower().split("x"))
    out = f"{base}_{w}x{h}.mp4"
    lvl = ["-level", "5.2"] if max(w, h) > 2000 else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", f"scale={w}:{h}:flags=lanczos",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", *lvl, "-pix_fmt", "yuv420p",
                    "-af", AF, "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", out], check=True)
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"],
                          capture_output=True, text=True).stderr.split("Summary:")[-1]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", meas); tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", meas)
    print(f"{out}  {os.path.getsize(out) / 1e6:.0f} MB  {i.group(1) if i else '?'} LUFS  true peak {tp.group(1) if tp else '?'} dBTP")
