import json, os, time
import numpy as np
from datetime import date, timedelta

t0 = time.time()
sst = np.load('/tmp/sst_region.npy')
meta = json.load(open('/tmp/meta.json'))
dates = [date.fromisoformat(d) for d in meta['dates']]
date_to_idx = {d: i for i, d in enumerate(dates)}
lat_region = np.array(meta['lat32'], dtype=np.float32)
lon_region = np.array(meta['lon32'], dtype=np.float32)
ND, NC = sst.shape

def doy(d):
    cum = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
    return cum[d.month] + d.day

tgt_dates = [date(2008,6,1) + timedelta(days=k) for k in range(92)]
tgt_idx = [date_to_idx[d] for d in tgt_dates]
S = sst[tgt_idx]
sea = np.isfinite(S).all(axis=0)
n_sea = int(sea.sum())
print("sea cells:", n_sea, "land:", NC - n_sea, "of", NC)
sea_idx = np.where(sea)[0]

base_dates = [date(1992,1,1) + timedelta(days=k) for k in range(4018)]
anchors = {d: [] for d in range(1, 367)}
for B in base_dates:
    dd = doy(B)
    if dd != 60:
        anchors[dd].append(B)

pool_rows = {}
for d in range(1, 367):
    if d == 60:
        pool_rows[d] = []
        continue
    rows = set()
    for B in anchors[d]:
        for k in range(-5, 6):
            X = B + timedelta(days=k)
            assert X in date_to_idx, X
            rows.add(date_to_idx[X])
    pool_rows[d] = np.sort(np.fromiter(rows, dtype=int))
psizes = [len(v) for k, v in pool_rows.items() if k != 60]
print("pool sizes min/max:", min(psizes), max(psizes))

thr_raw = np.full((n_sea, 366), np.nan)
clim_raw = np.full((n_sea, 366), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    V = sst[pool_rows[d]][:, sea_idx]
    good = ~np.isnan(V).all(axis=0)
    col = np.full(n_sea, np.nan)
    cm = np.full(n_sea, np.nan)
    if good.any():
        col[good] = np.nanquantile(V[:, good], 0.90, method='hazen', axis=0)
        cm[good] = np.nanmean(V[:, good], axis=0)
    thr_raw[:, d-1] = col
    clim_raw[:, d-1] = cm

thr_raw[:, 59] = (thr_raw[:, 58] + thr_raw[:, 60]) / 2.0
clim_raw[:, 59] = (clim_raw[:, 58] + clim_raw[:, 60]) / 2.0
print("NaNs after pools: thr", int(np.isnan(thr_raw).sum()), "clim", int(np.isnan(clim_raw).sum()))

rows_ = np.repeat(np.arange(366), 31)
cols_ = np.array([(i + k) % 366 for i in range(366) for k in range(-15, 16)])
W = np.zeros((366, 366))
W[rows_, cols_] = 1.0 / 31.0
assert np.allclose(W.sum(axis=1), 1.0)
thr_sm = thr_raw @ W.T
clim_sm = clim_raw @ W.T
assert thr_sm.shape == (n_sea, 366)
print("NaNs after smoothing: thr", int(np.isnan(thr_sm).sum()), "clim", int(np.isnan(clim_sm).sum()))
print("thr range over target doys:", float(thr_sm[:, 152:245].min()), float(thr_sm[:, 152:245].max()))
print("clim range over target doys:", float(clim_sm[:, 152:245].min()), float(clim_sm[:, 152:245].max()))

doy_tgt = np.array([doy(d) for d in tgt_dates])
thr_t = thr_sm[:, doy_tgt - 1].T
Ssea = S[:, sea_idx]
hot = Ssea >= thr_t
print("hot fraction:", round(float(hot.mean()), 4))

in_mhw = np.zeros((n_sea, 92), dtype=bool)
for c in range(n_sea):
    b = hot[:, c]
    ext = np.concatenate(([0], b.view(np.int8), [0]))
    dff = np.diff(ext)
    starts = np.where(dff == 1)[0]
    ends = np.where(dff == -1)[0]
    keep = (ends - starts) >= 5
    sk, ek = starts[keep], ends[keep]
    merged = []
    for s, e in zip(sk, ek):
        if merged and s - merged[-1][1] <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, int(e)])
    for s, e in merged:
        in_mhw[c, s:e] = True

active = in_mhw.any(axis=0)
events = []
in_ev = False
for t in range(92):
    if active[t] and not in_ev:
        start_t = t; in_ev = True
    elif not active[t] and in_ev:
        events.append((tgt_dates[start_t], tgt_dates[t-1])); in_ev = False
if in_ev:
    events.append((tgt_dates[start_t], tgt_dates[91]))
print("active days:", int(active.sum()), "of 92")
print("events:", [(str(a), str(b)) for a, b in events])
print("active day indices:", [int(i) for i in np.where(active)[0]])

np.savez('/tmp/mhw_intermediate.npz', thr_sm=thr_sm, clim_sm=clim_sm, in_mhw=in_mhw,
         active=active, sea_idx=sea_idx, doy_tgt=doy_tgt, thr_raw=thr_raw, clim_raw=clim_raw)
with open('/tmp/events.json', 'w') as f:
    json.dump({'events': [[str(a), str(b)] for a, b in events], 'n_sea': n_sea}, f)
print("phase done in", round(time.time()-t0, 1), "s")
