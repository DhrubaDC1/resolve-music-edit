"""Helpers for per-clip Fusion motion via the Resolve 21.2+ TimelineItem.AddEffect API.
Inspector keyframes (TimelineItem.AddKeyframe) do NOT exist in the scripting API; instead a Fusion
effect is added, gutted, and rebuilt as MediaIn -> Transform [-> Vortex] -> MediaOut with keyframes.
Comp frame 0 == the item's first timeline frame (measured)."""
from resolve_env import scriptapp

VESSEL = "Fusion/Fusion Effects/DVE"


def resolve():
    r = scriptapp()
    p = r.GetProjectManager().GetCurrentProject()
    return r, p, p.GetCurrentTimeline()


def timeline_by_name(p, name):
    for i in range(1, p.GetTimelineCount() + 1):
        if p.GetTimelineByIndex(i).GetName() == name:
            return p.GetTimelineByIndex(i)
    return None


def motion_comp(item, vortex=False):
    fx = item.AddEffect("fusion", VESSEL)
    assert fx, "AddEffect failed (needs Resolve Studio 21.2+)"
    comp = fx.GetFusionComp()
    tools = comp.GetToolList(False)
    mi = next(t for t in tools.values() if t.ID == "MediaIn")
    mo = next(t for t in tools.values() if t.ID == "MediaOut")
    comp.Lock()
    for t in tools.values():
        if t.ID not in ("MediaIn", "MediaOut"):
            t.Delete()
    xf = comp.AddTool("Transform", -32768, -32768); xf.SetAttrs({"TOOLS_Name": "XF"})
    xf.Input = mi.Output
    vx = None
    if vortex:
        vx = comp.AddTool("Vortex", -32768, -32768); vx.SetAttrs({"TOOLS_Name": "VX"})
        vx.Input = xf.Output; vx.Size = 1.25; vx.Power = 1.6; vx.Angle = 0; vx.MotionBlur = 1; vx.Quality = 4
        mo.Input = vx.Output
    else:
        mo.Input = xf.Output
    xf.MotionBlur = 1; xf.Quality = 6; xf.ShutterAngle = 220
    xf.Edges = 3            # mirror edges: zoom-outs / shakes / folds never show black
    comp.Unlock()
    return comp, xf, vx


def key(comp, tool, inp, pts, ease=0.0):
    """pts [(frame, value)]; point inputs take (x, y) and go through an XYPath.
    Build the spline fully, connect last (connecting first leaves a stray key). Handles are RELATIVE."""
    if isinstance(pts[0][1], (tuple, list)):
        xy = comp.XYPath()
        key(comp, xy, "X", [(f, v[0]) for f, v in pts], ease)
        key(comp, xy, "Y", [(f, v[1]) for f, v in pts], ease)
        tool[inp] = xy
        return
    spl = comp.BezierSpline(); kf = {}
    for i, (f, v) in enumerate(pts):
        k = {1: float(v)}
        if i > 0: k["LH"] = {1: -(f - pts[i - 1][0]) * ease, 2: 0}
        if i < len(pts) - 1: k["RH"] = {1: (pts[i + 1][0] - f) * ease, 2: 0}
        kf[float(f)] = k
    spl.SetKeyFrames(kf, True)
    tool[inp] = spl
