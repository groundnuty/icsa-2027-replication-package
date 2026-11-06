import json, time
import numpy as np
from datetime import date, timedelta

t0 = time.time()
sst = np.load('/tmp/sst_region.npy')
meta = json.load(open('/tmp/meta.json'))
dates = [date.fromisoformat(d) for d in meta['dates']]
date_to_idx = {d: i for i, d in enumerate(dates)}
NC = sst.shape[1]

def doy(d):
    cum = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
    return cum[d.month] + d.day

tgt_dates = [date(2008,6,1) + timedelta(days=k) for k in range(92)]
S = sst[[date_to_idx[d] for d in tgt_dates]]
sea = np.isfinite(S).all(axis=0)
n_sea = int(sea.sum())
sea_idx = np.where(sea)[0]
print("sea:", n_sea)

base_dates = [date(1992,1,1) + timedelta(days=k) for k in range(4018)]
pool_rows = {}
for d in range(1, 367):
    if d == 60:
        pool_rows[d] = []
        continue
    rows = set()
    for B in base_dates:
        if doy(B) == d:
            for k in range(-5, 6):
                rows.add(date_to_idx[B + timedelta(days=k)])
    pool_rows[d] = np.sort(np.fromiter(rows, dtype=int))

thr_raw = np.full((n_sea, 366), np.nan)
clim_raw = np.full((n_sea, 366), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    V = sst[pool_rows[d]][:, sea_idx]
    good = ~np.isnan(V).all(axis=0)
    col = np.full(n_sea, np.nan); cm = np.full(n_sea, np.nan)
    if good.any():
        col[good] = np.nanquantile(V[:, good], 0.90, method='hazen', axis=0)
        cm[good] = np.nanmean(V[:, good], axis=0)
    thr_raw[:, d-1] = col
    clim_raw[:, d-1] = cm
thr_raw[:, 59] = (thr_raw[:, 58] + thr_raw[:, 60]) / 2.0
clim_raw[:, 59] = (clim_raw[:, 58] + clim_raw[:, 60]) / 2.0

# ---- deterministic smoothing: direct mean of the 31 window values ----
def smooth366(A):
    out = np.empty_like(A)
    for i in range(366):
        idx = [(i + k) % 366 for k in range(-15, 16)]
        out[:, i] = A[:, idx].mean(axis=1)
    return out
thr_sm = smooth366(thr_raw)
clim_sm = smooth366(clim_raw)
assert not np.isnan(thr_sm).any() and not np.isnan(clim_sm).any()

doy_tgt = np.array([doy(d) for d in tgt_dates])
Ssea = S[:, sea_idx]

def mask_for(threshold):
    thr_t = threshold[:, doy_tgt - 1].T
    hot = Ssea >= thr_t
    in_mhw = np.zeros((n_sea, 92), dtype=bool)
    for c in range(n_sea):
        b = hot[:, c]
        ext = np.concatenate(([0], b.view(np.int8), [0]))
        dff = np.diff(ext)
        starts = np.where(dff == 1)[0]; ends = np.where(dff == -1)[0]
        keep = (ends - starts) >= 5
        merged = []
        for s, e in zip(starts[keep], ends[keep]):
            if merged and s - merged[-1][1] <= 2:
                merged[-1][1] = e
            else:
                merged.append([s, int(e)])
        for s, e in merged:
            in_mhw[c, s:e] = True
    return hot, in_mhw

hot, in_mhw = mask_for(thr_sm)
active = in_mhw.any(axis=0)

# robustness: perturb thresholds by +/-1e-9 K
hot_p, in_p = mask_for(thr_sm + 1e-9)
hot_m, in_m = mask_for(thr_sm - 1e-9)
print("mask identical under +1e-9:", (in_p == in_mhw).all(), " under -1e-9:", (in_m == in_mhw).all())
print("near-tie hot cells (|SST-thr| < 1e-9):", int((np.abs(Ssea - thr_sm[:, doy_tgt-1].T) < 1e-9).sum()))

events = []
in_ev = False
for t in range(92):
    if active[t] and not in_ev:
        start_t = t; in_ev = True
    elif not active[t] and in_ev:
        events.append((tgt_dates[start_t], tgt_dates[t-1])); in_ev = False
if in_ev:
    events.append((tgt_dates[start_t], tgt_dates[91]))
print("active days:", int(active.sum()))
print("events:", [(str(a), str(b)) for a, b in events])
print("active indices:", [int(i) for i in np.where(active)[0]])

np.savez('/tmp/mhw_final.npz', thr_sm=thr_sm, clim_sm=clim_sm, in_mhw=in_mhw,
         active=active, sea_idx=sea_idx, doy_tgt=doy_tgt, thr_raw=thr_raw, clim_raw=clim_raw)
with open('/tmp/events_final.json', 'w') as f:
    json.dump({'events': [[str(a), str(b)] for a, b in events], 'n_sea': n_sea}, f)
print("done in", round(time.time()-t0, 1), "s")
