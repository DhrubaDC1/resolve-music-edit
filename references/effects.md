# Effects catalogue (what build.py can do, and what each looks like)

## Cut types (value of edit.json "cuts", keyed by the INCOMING shot index)
All motion is a keyframed Fusion Transform (motion blur, shutter 220°, mirror edges) on the clip itself, so it
needs no media handles. Curves start moving on the cut frame (a curve that holds before frame 0 leaves the cut
frame sharp and frozen — that bug was fixed; keep `(x+1)/(n+1)`).

| type | outgoing tail | incoming head | use for |
|---|---|---|---|
| cut | — | — | subtle edits |
| punch | — | zoom 1.22→1 in 5f | bursts, beat hits |
| zoom | zoom 1→3.2 last 4f | zoom 2.5→1 in 5f | zoom-through; THE drop |
| whipL / whipR | slide off 3f | slide in 4f | between movement shots |
| spin | rotate 30°, zoom 1.9 | -30°→0 | non-inception spin |
| roll (inception) | rotate 90°, zoom 2.2 last 6f | -90°→0 in 8f | barrel roll, continuous direction |
| vortex (inception) | Vortex tool twist 0→620° last 7f | unwinds 620→0 in 9f | swirl into heroes / finale |
| fold (inception) | shrink to .38 + rotate 135° → mirrored kaleidoscope city | unfolds in 10f | Inception city-fold |
| ["T", name, frames] | native Resolve Fusion transition (needs handles: centre needs frames/2 each side) | | glitch/light/warp |

Measured-good native Fusion transitions (category "fusion"; exact names):
Crash Zoom (radial zoom blur), Tunnel of Light (light-streak burst — spectacular into heroes), Glitch,
Block Glitch, RGB Splitter, Slice Push, Shash, Warp, Drop Warp, Ripple Warp, Inverse Flash, Three Color Flash,
Brightness Flash, Camera Shake, Stretch Blur, Spin, Zoom In and Out, Pan Left/Right/Up/Down, Circle Spin, Fold,
Cube, Flip 3D, Box Twist, Page Curl, Mosaic*, Shatter, Paint On … ("Cross Dissolve" uses category "simple").
Full list (Linux path; it's a zip): unzip -l /opt/resolve/Fusion/Templates/Templates.drfx | grep Edit/Transitions — or the
Effects library > Video Transitions > Fusion Transitions in the Edit page.

## Inner motion by role (automatic)
- wide: push-in 1→1.10 + small pulse every beat
- hero: push-in 1→1.08 + pulse .18 on its first beat, .09 on every later beat (the "pulse to the music" look)
- "" (normal): push-in 1→1.05 + pulse on its 2nd beat
- burst / whip: handheld shake (±1.6% position, ±2.2°), base zoom 1.08; speed 140% / 200%
- the drop shot: big decaying shake
- finale: 60% optical-flow slow-mo + push-in 1→1.15

## Look stack
CDL (slope/offset/power/sat) with per-clip exposure match (target mean luma 72 of 255, gain clamp .85-1.35),
OFX **Halation** on every clip (default params look filmic). OFX **Glow** default is too strong (washes neon) — avoid.
Overlays: leaks (Screen; white flash on the drop, warm blooms on heroes, magenta every 2 bars, strobe into the
finale), titles (Screen), grain (Overlay 45%), vignette (Multiply).

## Other 21.2 effects reachable via AddEffect (defaults only for OFX — parameters are not scriptable)
OFX: Film Grain, Halation, Glow, Light Rays, Lens Flare, Aperture Diffraction, Camera Shake, Motion Blur,
Prism Blur, Chromatic Aberration Removal, Film Look Creator, Analog Damage, Film Damage, JPEG Damage, Scanlines,
Lens Distortion, Vortex, Ripples, Waviness, Mirrors, Tilt-Shift Blur, Zoom Blur, Vignette, Flicker Addition.
Fusion (comp editable/keyframable): DVE (PiP by default!), Digital Glitch, Hologram Glitch, Noise Distortion,
CCTV, Video Camera, Night Vision, Comic Book, Slice, Stretch Region, Highlight Stretch.
Fusion tools usable inside a motion comp: Transform, Vortex (Center/Size/Angle/Power), Dent, CoordSpace, Blur…
Test any new effect with a 2-second `render_range.py` excerpt and look at the frames before using it widely.
