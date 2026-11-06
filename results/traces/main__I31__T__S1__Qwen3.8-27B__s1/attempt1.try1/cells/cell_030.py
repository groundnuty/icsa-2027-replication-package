
import numpy as np, datetime

thr_s = np.load('work/thr_smooth.npy')
S_tgt = np.load('work/S_tgt.npy')
N = 3600; T = 92
sea = np.load('work/sea.npy')
t0 = datetime.date(2017,6,1)
tgt_dates = [t0 + datetime.timedelta(days=i) for i in range(T)]
dbm = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
doy_t = np.array([dbm[d.month] + d.day for d in tgt_dates])
S64 = S_tgt.astype(np.float64).reshape(T, N)
H = (S64 >= thr_s[doy_t]) & sea[None, :]
assert H.sum() == 338

padded = np.concatenate([np.zeros((1, N), np.int8), H.astype(np.int8), np.zeros((1, N), np.int8)], axis=0)
d = np.diff(padded, axis=0)
si = np.where(d == 1); ei = np.where(d == -1)
print("n runs:", si[0].size, "n ends:", ei[0].size)
assert si[0].size == ei[0].size
runs = {}
for c, s, e in zip(si[1], si[0]-1, ei[0]-2):
    runs.setdefault(int(c), []).append((int(s), int(e)))
maxrun = max(e-s+1 for rs in runs.values() for s, e in rs)
print("cells with runs:", len(runs), "max consecutive hot days:", maxrun)
l4 = [(c, rs) for c, rs in runs.items() for s, e in rs if e - s + 1 == 4]
print("4-day runs:", len(l4))
for c, rs in l4[:3]: print("  cell", c, rs)
# distribution of run lengths
from collections import Counter
lc = Counter(e-s+1 for rs in runs.values() for s, e in rs)
print("run length distribution:", dict(sorted(lc.items())))

mask = np.zeros((T, N), dtype=np.uint8)
nseg = 0
for c, rs in runs.items():
    segs = []
    for s, e in rs:
        if e - s + 1 < 5: continue
        if segs and s - segs[-1][1] - 1 <= 2: segs[-1][1] = e
        else: segs.append([s, e])
    nseg += len(segs)
    for s, e in segs: mask[s:e+1, c] = 1
print("per-cell MHW segments:", nseg, "mask cell-days:", int(mask.sum()))

active = mask.any(axis=1)
evd = np.diff(np.concatenate([[0], active.astype(int), [0]]))
onsets = np.where(evd == 1)[0]; ends = np.where(evd == -1)[0]
events = [(str(tgt_dates[o]), str(tgt_dates[e-1])) for o, e in zip(onsets, ends)]
print("active days:", int(active.sum()), "events:", events)
np.save('work/mask_final.npy', mask)
print("FINAL DONE")
