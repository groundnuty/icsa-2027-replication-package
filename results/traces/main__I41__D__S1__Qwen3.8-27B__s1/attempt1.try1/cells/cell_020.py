import pickle, numpy as np
from datetime import date, timedelta

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
base_dates = dd['base']; tgt_dates = dd['tgt']
nb = len(base_dates)
SST = np.load('/work/SST_all.npy')
sea_mask = np.load('/work/sea_mask.npy')
pool_idx = pickle.load(open('/work/pool_idx.pkl','rb'))

def mdoy(dt):
    return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

# ---- per-day threshold (hazen p90) and climatology (mean) ----
thr = np.full((366, 3600), np.nan)
clim = np.full((366, 3600), np.nan)
for D in range(1, 367):
    if D == 60: continue
    P = SST[np.array(pool_idx[D])]          # (121, 3600)
    clim[D-1] = np.nanmean(P, axis=0)
    # hazen p90 with NaN handling
    mask = np.isnan(P)
    Ps = np.where(mask, np.inf, P)
    S = np.sort(Ps, axis=0)
    n = (~mask).sum(axis=0)
    r = (n - 1) * 0.9
    lo = np.floor(r).astype(np.int64); hi = np.ceil(r).astype(np.int64)
    frac = r - lo
    c = np.arange(3600)
    val = S[lo, c] * (1 - frac) + S[hi, c] * frac
    val = np.where(n == 0, np.nan, val)
    thr[D-1] = val
# day 60
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

# ---- 31-day centred wrap-around moving mean over 366-day arrays ----
def smooth31(x):
    # x: (366, 3600); out[d] = mean of x[d-15..d+15] mod 366
    x3 = np.concatenate([x, x, x], axis=0)
    cnt = (~np.isnan(x3)).sum(axis=0)          # (1098, 3600)
    csum = np.concatenate([np.zeros((1,3600)), np.nancumsum(x3, axis=0)], axis=0)
    out = np.full(x.shape, np.nan)
    for d in range(366):
        w = x3[d:d+31]
        s = np.nansum(w, axis=0)
        c = (~np.isnan(w)).sum(axis=0)
        out[d] = np.where(c > 0, s / np.maximum(c,1), np.nan)
    return out

thr_s = smooth31(thr)
clim_s = smooth31(clim)
np.save('/work/thr_raw.npy', thr); np.save('/work/clim_raw.npy', clim)
np.save('/work/thr_smooth.npy', thr_s); np.save('/work/clim_smooth.npy', clim_s)

print("thr finite (sea cells):", np.isfinite(thr_s[:, sea_mask.ravel()]).all() if sea_mask.any() else None)
print("thr range (sea, smoothed):", np.nanmin(thr_s[:, sea_mask.ravel()]), np.nanmax(thr_s[:, sea_mask.ravel()]))
print("clim range (sea, smoothed):", np.nanmin(clim_s[:, sea_mask.ravel()]), np.nanmax(clim_s[:, sea_mask.ravel()]))

# ---- target period: hot days ----
tgt = SST[nb:].copy()
doys = np.array([mdoy(d) for d in tgt_dates])
print("target doy range:", doys.min(), doys.max())
thr_t = thr_s[doys - 1]   # (92, 3600)
hot = np.where(sea_mask, tgt >= thr_t, False)  # NaN comparison False anyway
print("hot days total:", hot.sum(), "of", 92*3308)

# ---- per-cell MHWs: runs >=5, merge gaps of 1-2 ----
n_t = len(tgt_dates)
mhw = np.zeros((n_t, 3600), dtype=np.uint8)
for c in range(3600):
    h = hot[:, c]
    if not h.any(): continue
    d = np.diff(np.concatenate([[0], h.view(np.int8), [0]]))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0] - 1
    runs = [(s, e) for s, e in zip(starts, ends) if (e - s + 1) >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    for s, e in merged:
        mhw[s:e+1, c] = 1
np.save('/work/mhw.npy', mhw)
print("MHW cell-days:", mhw.sum())

active = mhw.any(axis=1)
# regional events
ev = []
d = np.diff(np.concatenate([[0], active.view(np.int8), [0]]))
st = np.where(d == 1)[0]; en = np.where(d == -1)[0] - 1
for s, e in zip(st, en):
    ev.append((tgt_dates[s].isoformat(), tgt_dates[e].isoformat(), e - s + 1))
print("regional events:", len(ev))
for e in ev: print("  ", e)
pickle.dump(ev, open('/work/events.pkl','wb'))
