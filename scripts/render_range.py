"""render_range.py OUT_DIR NAME IN OUT [W H [CODEC]]   (frames relative to timeline start; blocking)
OUT_DIR must be inside a Resolve Media Storage location ("Render path inaccessible" otherwise).
Renders an intermediate .mov (ProRes, falling back to DNxHR where ProRes is unavailable); make the
social mp4 with deliver.py (Linux Resolve has no H.264 encoder at all).
CODEC default: ProRes422HQ (>= 2000 px) else ProRes422P (proxy, for previews)."""
import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_env import scriptapp

out, name, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
w, h = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (1080, 1920)
codec = sys.argv[7] if len(sys.argv) > 7 else ("ProRes422HQ" if w >= 2000 else "ProRes422P")
r = scriptapp(); p = r.GetProjectManager().GetCurrentProject(); t = p.GetCurrentTimeline()
page = r.GetCurrentPage()
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    if f.startswith(name + "."): os.remove(os.path.join(out, f))
p.DeleteAllRenderJobs()
FALLBACK = {"ProRes422HQ": ["DNxHRHQX_10", "DNxHRHQ"], "ProRes422P": ["DNxHRLB", "DNxHRSQ"]}
for c in [codec] + FALLBACK.get(codec, []):
    if p.SetCurrentRenderFormatAndCodec("mov", c): codec = c; break
else:
    raise SystemExit(f"no usable mov codec among {[codec] + FALLBACK.get(codec, [])}: {p.GetRenderCodecs('mov')}")
s0 = t.GetStartFrame()
assert p.SetRenderSettings({"SelectAllFrames": False, "MarkIn": s0 + a, "MarkOut": s0 + b, "TargetDir": out,
                            "CustomName": name, "FormatWidth": w, "FormatHeight": h, "ExportVideo": True, "ExportAudio": True})
job = p.AddRenderJob(); assert job, "AddRenderJob failed: is OUT_DIR inside Resolve's Media Storage?"
assert p.StartRendering([job], False), "StartRendering returned False"
t0 = time.time()
while p.IsRenderingInProgress(): time.sleep(1)
st = p.GetRenderJobStatus(job); print(t.GetName(), codec, st, f"{time.time() - t0:.0f}s")
p.DeleteRenderJob(job)
if page: r.OpenPage(page)
assert st.get("JobStatus") == "Complete", st
print(os.path.join(out, name + ".mov"))
