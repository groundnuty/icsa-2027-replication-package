
import numpy as np, datetime

thr_s = np.load('work/thr_smooth.npy')
S_tgt = np.load('work/S_tgt.npy')
N = 3600; T = 92
mday = [31,29,31,30,31,30,31,31,30,31,30,31]
cdf_prev = np.concatenate([[0], np.cumsum(mday)[:-1]])
t0 = datetime.date(2017,6,1)
tgt_dates = [t0 + datetime.timedelta(days=i) for i in range(T)]
doy_t = cdf_prev[np.array([d.month for d in tgt_dates])-1] + np.array([d.day for d in tgt_dates])
assert doy_t.min() == 152 and doy_t.max() == 243, (doy_t.min(), doy_t.max())

sea = np.isfinite(S_tgt).all(axis=0).reshape(-1)
S64 = S_tgt.astype(np.float64).reshape(T, N)
H = (S64 >= thr_s[doy_t]) & sea[None, :]
print("H shape:", H.shape, "hot days:", int(H.sum()), "cells with any hot day:", int(H.any(axis=0).sum()))
print("hot frac Jun30 (sea cells):", float(H[29][sea].mean()), " Jul15:", float(H[44][sea].mean()), " Aug31:", float(H[91][sea].mean()))
np.save('work/H.npy', H)
np.save('work/sea.npy', sea)

# ---- per-cell MHW: maximal hot runs >=5 days; merge runs separated by <=2 non-hot days
d = np.diff(np.concatenate([np.zeros((1, N), bool), H, np.zeros((1, N), bool)], axis=0), axis=0)
si = np.where(d == 1); ei = np.where(d == -1)
start_day = si[0] - 1
end_day = ei[0] - 2
cell_ids = si[1]
assert len(start_day) == len(end_day)
# verify alignment: for each cell, starts and ends interleave and start<end
ok = True
per_cell = {}
for c, s, e in zip(cell_ids, start_day, end_day):
    per_cell.setdefault(int(c), []).append((int(s), int(e)))
for c, runs in per_cell.items():
    for s, e in runs:
        if not (0 <= s <= e < T): ok = False
    for k in range(len(runs)-1):
        if runs[k+1][0] <= runs[k][1]: ok = False
assert ok
print("total runs:", sum(len(v) for v in per_cell.values()))

mask = np.zeros((T, N), dtype=np.uint8)
n_segs = 0
for c, runs in per_cell.items():
    segs = []
    for s, e in runs:
        if e - s + 1 < 5:
            continue
        if segs and s - segs[-1][1] - 1 <= 2:
            segs[-1][1] = e
        else:
            segs.append([s, e])
    n_segs += len(segs)
    for s, e in segs:
        mask[s:e+1, c] = 1
print("per-cell MHW segments:", n_segs, " masked cell-days:", int(mask.sum()))
np.save('work/mask.npy', mask)

active = mask.any(axis=1)
evd = np.diff(np.concatenate([[0], active.astype(int), [0]]))
onsets = np.where(evd == 1)[0]; ends = np.where(evd == -1)[0]
print("active days:", int(active.sum()), "of", T)
events = [(str(tgt_dates[o]), str(tgt_dates[e-1]), int(e-o)) for o, e in zip(onsets, ends)]
for ev in events: print("event:", ev)
