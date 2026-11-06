import json, os, time
import numpy as np
import xarray as xr
from datetime import date, timedelta

t0 = time.time()
sst = np.load('/tmp/sst_region.npy')
meta = json.load(open('/tmp/meta.json'))
dates = [date.fromisoformat(d) for d in meta['dates']]
date_to_idx = {d: i for i, d in enumerate(dates)}
lat_region = np.array(meta['lat32'], dtype=np.float32)
lon_region = np.array(meta['lon32'], dtype=np.float32)
ND, NC = sst.shape
print("stack:", sst.shape, "loaded in", round(time.time()-t0, 1), "s")

def doy(d):
    cum = {1:0, 2:31, 3:61, 4:92, 5:122, 6:153, 7:183, 8:214, 9:245, 10:275, 11:306, 12:336}
    return cum[d.month] + d.day

# sanity of mapping
assert doy(date(2000,2,28)) == 59 and doy(date(2000,2,29)) == 60 and doy(date(2000,3,1)) == 61
assert doy(date(2008,1,1)) == 1 and doy(date(2008,12,31)) == 366
assert doy(date(2008,6,1)) == 153 and doy(date(2008,8,31)) == 244

# ---- target block & sea cells ----
tgt_dates = [date(2008,6,1) + timedelta(days=k) for k in range(92)]
tgt_idx = [date_to_idx[d] for d in tgt_dates]
S = sst[tgt_idx]                      # (92, NC)
sea = np.isfinite(S).all(axis=0)      # (NC,)
n_sea = int(sea.sum())
print("sea cells:", n_sea, "land:", NC - n_sea, "of", NC)
sea_idx = np.where(sea)[0]

# ---- baseline pools ----
base_dates = [date(1992,1,1) + timedelta(days=k) for k in range(4018)]
assert base_dates[-1] == date(2002,12,31)
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

# max pool size check
print("pool sizes: min", min(len(v) for k,v in pool_rows.items() if k!=60),
      "max", max(len(v) for k,v in pool_rows.items() if k!=60))

thr_raw = np.full((n_sea, 366), np.nan)
clim_raw = np.full((n_sea, 366), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    V = sst[pool_rows[d]][:, sea_idx]          # (nrows, n_sea)
    good = ~np.isnan(V).all(axis=0)
    col = np.full(n_sea, np.nan)
    cm = np.full(n_sea, np.nan)
    if good.any():
        col[good] = np.nanquantile(V[:, good], 0.90, method='hazen', axis=0)
        cm[good] = np.nanmean(V[:, good], axis=0)
    thr_raw[:, d-1] = col
    clim_raw[:, d-1] = cm

# day 60 = mean of 59 and 61
thr_raw[:, 59] = (thr_raw[:, 58] + thr_raw[:, 60]) / 2.0
clim_raw[:, 59] = (clim_raw[:, 58] + clim_raw[:, 60]) / 2.0
print("NaNs after pools: thr", int(np.isnan(thr_raw).sum()), "clim", int(np.isnan(clim_raw).sum()))

# ---- 31-day centred wrapped moving mean ----
W = np.zeros((366, 366))
for i in range(366):
    W[i, (i - 15) % 366 : (i + 15) % 366 + 1] if False else None
rows_ = []
cols_ = []
for i in range(366):
    js = [(i + k) % 366 for k in range(-15, 16)]
    rows_ += [i]*31
    cols_ += js
W = np.zeros((366, 366))
W[np.repeat(np.arange(366), 31), np.array(cols_)] = 1.0/31.0
assert np.allclose(W.sum(axis=1), 1.0)
thr_sm = W @ thr_raw
clim_sm = W @ clim_raw
print("NaNs after smoothing: thr", int(np.isnan(thr_sm).sum()), "clim", int(np.isnan(clim_sm).sum()))

# ---- hot days & per-cell MHWs over target ----
doy_tgt = np.array([doy(d) for d in tgt_dates])          # (92,)
thr_t = thr_sm[:, doy_tgt - 1].T                        # (92, n_sea)
Ssea = S[:, sea_idx]                                     # (92, n_sea)
hot = Ssea >= thr_t
print("hot fraction:", float(hot.mean()))

in_mhw = np.zeros((n_sea, 92), dtype=bool)
for c in range(n_sea):
    b = hot[:, c]
    ext = np.concatenate(([0], b.view(np.int8), [0]))
    dff = np.diff(ext)
    starts = np.where(dff == 1)[0]
    ends   = np.where(dff == -1)[0]
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

np.save('/tmp/computed.npy', np.concatenate([
    thr_raw.reshape(-1)[0:0],  # keep small
]))
# save needed intermediates
np.savez('/tmp/mhw_intermediate.npz',
         thr_sm=thr_sm, clim_sm=clim_sm, in_mhw=in_mhw, active=active,
         sea_idx=sea_idx, doy_tgt=doy_tgt)
with open('/tmp/events.json', 'w') as f:
    json.dump({'events': [[str(a), str(b)] for a, b in events], 'n_sea': n_sea}, f)
print("phase done in", round(time.time()-t0, 1), "s")
