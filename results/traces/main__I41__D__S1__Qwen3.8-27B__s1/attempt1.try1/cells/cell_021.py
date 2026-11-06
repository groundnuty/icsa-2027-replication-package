import pickle, numpy as np, warnings
from datetime import date, timedelta

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
tgt_dates = dd['tgt']
nb = len(dd['base'])
SST = np.load('/work/SST_all.npy')
sea_mask = np.load('/work/sea_mask.npy')
pool_idx = pickle.load(open('/work/pool_idx.pkl','rb'))

def mdoy(dt):
    return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

thr = np.full((366, 3600), np.nan)
clim = np.full((366, 3600), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for D in range(1, 367):
        if D == 60: continue
        P = SST[np.array(pool_idx[D])].reshape(-1, 3600)   # (121, 3600)
        clim[D-1] = np.nanmean(P, axis=0)
        mask = np.isnan(P)
        Ps = np.where(mask, np.inf, P)
        S = np.sort(Ps, axis=0)
        n = (~mask).sum(axis=0)
        r = (n - 1) * 0.9
        lo = np.floor(r).astype(np.int64); hi = np.ceil(r).astype(np.int64)
        frac = r - lo
        c = np.arange(3600)
        val = S[lo, c] * (1 - frac) + S[hi, c] * frac
        thr[D-1] = np.where(n == 0, np.nan, val)
# day 60 = mean of 59 and 61
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

def smooth31(x):
    x3 = np.concatenate([x, x, x], axis=0)
    out = np.full(x.shape, np.nan)
    for d in range(366):
        w = x3[d:d+31]
        s = np.nansum(w, axis=0)
        c = (~np.isnan(w)).sum(axis=0)
        out[d] = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    return out

thr_s = smooth31(thr)
clim_s = smooth31(clim)
np.save('/work/thr_raw.npy', thr); np.save('/work/clim_raw.npy', clim)
np.save('/work/thr_smooth.npy', thr_s); np.save('/work/clim_smooth.npy', clim_s)

sc = sea_mask.ravel()
print("thr_smooth finite for sea cells:", np.isfinite(thr_s[:, sc]).all())
print("thr_smooth range (sea):", np.nanmin(thr_s[:, sc]), np.nanmax(thr_s[:, sc]))
print("clim_smooth range (sea):", np.nanmin(clim_s[:, sc]), np.nanmax(clim_s[:, sc]))
print("day60 vs 59/61 check:", np.allclose(thr_s[59], thr_s[59]))

tgt = SST[nb:]
doys = np.array([mdoy(d) for d in tgt_dates])
print("target doy range:", doys.min(), doys.max())
thr_t = thr_s[doys - 1]
hot = (tgt >= thr_t) & sea_mask
print("hot cell-days:", int(hot.sum()))

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
print("MHW cell-days (incl. gap days):", int(mhw.sum()))

active = mhw.any(axis=1)
d = np.diff(np.concatenate([[0], active.view(np.int8), [0]]))
st = np.where(d == 1)[0]; en = np.where(d == -1)[0] - 1
ev = [(tgt_dates[s].isoformat(), tgt_dates[e].isoformat(), int(e - s + 1)) for s, e in zip(st, en)]
print("regional events:", len(ev))
for e in ev: print("  ", e)
pickle.dump(ev, open('/work/events.pkl','wb'))
