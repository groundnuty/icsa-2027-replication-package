import numpy as np, pickle
from datetime import datetime

with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/thr.pkl","rb") as f: T = pickle.load(f)

sst_target = D["sst_target"]           # (92, 60, 60)
sea = D["sea"]
cell_idx = T["cell_idx"]
thr_s = T["thr_s"]                     # (366, nc)
time_target = D["time_target"]         # 92 datetimes

CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_t = np.array([CUM[dt.month-1] + dt.day for dt in time_target])
print("doy target range:", doy_t.min(), doy_t.max(), "unique count:", len(np.unique(doy_t)))
assert (doy_t == np.arange(153, 245)).all()

sst_c = sst_target[:, cell_idx, :]     # (92, nc)
thr_c = thr_s[doy_t, :]                # (92, nc)
hot = sst_c >= thr_c                   # (92, nc)
print("hot fraction:", hot.mean(), "max per day:", hot.any(axis=1).mean())
print("cells ever hot:", hot.any(axis=0).sum(), "of", len(cell_idx))

def runs_of(mask):
    """maximal runs of True -> list of (start, end) 0-based inclusive"""
    out = []
    n = len(mask)
    i = 0
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j+1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out

nc = len(cell_idx)
mhw_mask = np.zeros((92, nc), dtype=bool)
n_events_per_cell_hist = {}
for c in range(nc):
    r = [r for r in runs_of(hot[:, c]) if r[1] - r[0] + 1 >= 5]
    # join runs separated by 1 or 2 non-hot days
    merged = []
    for s, e in r:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    for s, e in merged:
        mhw_mask[s:e+1, c] = True
    n_events_per_cell_hist[len(merged)] = n_events_per_cell_hist.get(len(merged), 0) + 1

print("cells by #MHWs:", dict(sorted(n_events_per_cell_hist.items())))
print("cells with >=1 MHW:", (mhw_mask.any(axis=0)).sum())

active = mhw_mask.any(axis=1)
print("active days:", active.sum(), "of 92")
aruns = runs_of(active)
events = [(time_target[s].strftime("%Y-%m-%d"), time_target[e].strftime("%Y-%m-%d"), e-s+1) for s, e in aruns]
for ev in events:
    print("event:", ev[0], "->", ev[1], "len", ev[2])

import json
with open("/tmp/mhw_state.pkl","wb") as f:
    pickle.dump({"mhw_mask": mhw_mask, "events": [(e[0], e[1]) for e in events],
                 "active": active, "hot": hot}, f)
print("saved")
