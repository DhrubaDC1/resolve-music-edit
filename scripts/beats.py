"""beats.py MUSIC_FILE WORK_DIR

Tempo, beats, downbeats, per-second loudness/bass, and candidate DROPS (biggest bass jumps on a
downbeat) and BREAKDOWNS (sustained low bass). Writes WORK/beats.json and prints an ASCII energy map
so you can choose the music window (music.in / drop / final / bass_end / out in edit.json).
"""
import sys, json, numpy as np, librosa

y, sr = librosa.load(sys.argv[1], sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
tempo = float(np.atleast_1d(tempo)[0]); dur = len(y) / sr
hop = 512
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
S = np.abs(librosa.stft(y, hop_length=hop)); freqs = librosa.fft_frequencies(sr=sr)
bass = S[freqs < 150].mean(axis=0)
t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
secs = [(float(rms[(t >= s) & (t < s + 1)].mean()), float(bass[(t >= s) & (t < s + 1)].mean())) for s in range(int(np.ceil(dur)))]
r = np.array([a for a, _ in secs]); b = np.array([c for _, c in secs]); r /= r.max(); b /= b.max()

bf = librosa.time_to_frames(beats, sr=sr, hop_length=hop)
bb = bass[np.clip(bf, 0, len(bass) - 1)]
phase = int(np.argmax([bb[p::4].mean() for p in range(4)]))
down = beats[phase::4]

# drop candidates: downbeat where mean bass of the next 2 bars >> previous 2 bars
def win(a, c): m = (t >= a) & (t < c); return bass[m].mean() if m.any() else 0
cands = []
for k in range(2, len(down) - 2):
    before, after = win(down[k - 2], down[k]), win(down[k], down[k + 2])
    if before > 0: cands.append((float(after / before), float(down[k])))
cands = sorted(cands, reverse=True)
drops = []
for ratio, tt in cands:
    if ratio < 1.25: break
    if all(abs(tt - d) > 8 for _, d in drops): drops.append((ratio, tt))
    if len(drops) == 4: break
quiet = [s for s in range(len(b)) if b[s] < 0.35]

json.dump(dict(tempo=tempo, duration=dur, beats=[round(float(x), 3) for x in beats],
               downbeats=[round(float(x), 3) for x in down], loud=r.round(2).tolist(), bass=b.round(2).tolist(),
               drop_candidates=[dict(time=round(tt, 3), ratio=round(q, 2)) for q, tt in drops]),
          open(f"{sys.argv[2]}/beats.json", "w"))
print(f"tempo {tempo:.1f} BPM | beat {60 / tempo:.3f}s | bar {240 / tempo:.3f}s | {len(beats)} beats | duration {dur:.1f}s")
print("drop candidates (downbeat, bass ratio after/before):", [(round(tt, 2), round(q, 2)) for q, tt in sorted(drops, key=lambda x: x[1])])
print("sec  loudness                       bass")
for s in range(len(r)):
    tag = " <- DROP?" if any(int(tt) == s for _, tt in drops) else ""
    print(f"{s:3d}  {'#' * int(r[s] * 30):30s} {'=' * int(b[s] * 20):20s}{tag}")
print("downbeats:", [round(float(x), 2) for x in down])
