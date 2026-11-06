import numpy as np
from datetime import date, timedelta
S_tgt = np.load('/work/S_tgt.npy')     # (92, 60, 60)
thr_s = np.load('/work/thr_s.npy')     # (366, 3600)
lat_vals = np.load('/work/lat_vals.npy'); lon_vals = np.load('/work/lon_vals.npy')

tgt_dates = []
d = date(2021,6,1)
while d <= date(2021,8,31):
    tgt_dates.append(d); d += timedelta(days=1)
def doy_of(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1
doy_tgt = np.array([doy_of(dt) for dt in tgt_dates])
print("doy target range:", doy_tgt.min(), doy_tgt.max(), "n:", len(doy_tgt))

hot = S_tgt >= thr_s[doy_tgt-1].reshape(len(doy_tgt), 60, 60)
print("hot frac (all cells):", hot.mean(), " (land cells all False:", (~np.isfinite(S_tgt).all(axis=0)).reshape(-1) @ hot.reshape(len(doy_tgt), -1).sum() == 0, ")")
sea = np.isfinite(S_tgt).all(axis=0).reshape(-1)
print("hot frac (sea cells):", hot.reshape(len(doy_tgt), -1)[:, sea].mean())

# per-cell MHWs
Nt = len(doy_tgt)
mask = np.zeros((Nt, 60, 60), dtype=np.uint8)
hflat = hot.reshape(Nt, 3600)
n_mhw_per_cell = np.zeros(3600, dtype=int)
for c in range(3600):
    if not sea[c]:
        continue
    h = hflat[:, c]
    padded = np.concatenate(([0], h.view(np.int8), [0]))
    dd = np.diff(padded)
    starts = np.where(dd == 1)[0]
    ends = np.where(dd == -1)[0] - 1  # inclusive ends
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    n_mhw_per_cell[c] = len(merged)
    for s, e in merged:
        mask[s:e+1, c//60, c%60] = 1

print("cells with >=1 MHW:", (n_mhw_per_cell > 0).sum())
print("MHWs per cell: min/max/mean:", n_mhw_per_cell.min(), n_mhw_per_cell.max(), n_mhw_per_cell[sea].mean())

# regional activity
active = mask.any(axis=(1, 2))
print("active days:", int(active.sum()), "of", Nt)
# regional events: maximal runs of active days
padded = np.concatenate(([False], active, [False]))
dd = np.diff(padded.astype(np.int8))
s_idx = np.where(dd == 1)[0]
e_idx = np.where(dd == -1)[0] - 1
events = [(s_idx[i], e_idx[i]) for i in range(len(s_idx))]
for s, e in events:
    print("event:", tgt_dates[s], "->", tgt_dates[e], f"({e-s+1} days)")
np.save('/work/mask.npy', mask)
np.save('/work/events.npy', np.array(events) if events else np.zeros((0,2), dtype=int))
