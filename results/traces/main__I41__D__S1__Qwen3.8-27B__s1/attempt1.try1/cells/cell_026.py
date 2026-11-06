import pickle, numpy as np, warnings, time
from datetime import date

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
base_dates, tgt_dates = dd['base'], dd['tgt']
nb = len(base_dates)
SST = np.load('/work/SST_all.npy')
sea_mask = np.load('/work/sea_mask.npy').ravel()
pool_idx = pickle.load(open('/work/pool_idx.pkl','rb'))

def mdoy(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

t0 = time.time()
thr = np.full((366, 3600), np.nan)
clim = np.full((366, 3600), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for D in range(1, 367):
        if D == 60: continue
        P = SST[np.array(pool_idx[D])].reshape(-1, 3600)
        clim[D-1] = np.nanmean(P, axis=0)
        thr[D-1] = np.nanquantile(P, 0.9, method='hazen', axis=0)
# day 60 = mean of days 59 and 61 (before smoothing)
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0
print("threshold/clim time:", time.time()-t0)

# correct centred 31-day wrap-around moving mean
def smooth31(x):
    x3 = np.concatenate([x, x, x], axis=0)                 # (1098, 3600)
    fin = ~np.isnan(x3)
    csum = np.cumsum(np.where(fin, x3, 0.0), axis=0)
    ccnt = np.cumsum(fin, axis=0)
    out = np.full(x.shape, np.nan)
    for d in range(366):
        a, b = d + 351, d + 382    # window x3[a:b] == days d-15..d+15 mod 366
        s = csum[b-1] - (csum[a-1] if a > 0 else 0.0)
        c = ccnt[b-1] - (ccnt[a-1] if a > 0 else 0)
        out[d] = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    return out

thr_s = smooth31(thr)
clim_s = smooth31(clim)

# ---- validate smoothing independently ----
def smooth31_ref(x):
    out = np.full(x.shape, np.nan)
    for d in range(366):
        vals = [x[(d+k) % 366] for k in range(-15, 16)]
        out[d] = np.nanmean(vals, axis=0)
    return out
print("smooth31 match:", np.allclose(smooth31(thr), smooth31_ref(thr), equal_nan=True))
print("smooth31 clim match:", np.allclose(smooth31(clim), smooth31_ref(clim), equal_nan=True))

# spot-check a specific day window: day 0 (1 Jan) should average days 351..365, 0..15
d0 = 0
manual = np.nanmean(np.concatenate([thr[351:366], thr[0:16]], axis=0), axis=0)
print("day0 window check:", np.allclose(thr_s[0], manual))
# day 20 (21 Jan): days 5..35
manual20 = np.nanmean(thr[5:36], axis=0)
print("day20 window check:", np.allclose(thr_s[20], manual20))

np.save('/work/thr_raw.npy', thr); np.save('/work/clim_raw.npy', clim)
np.save('/work/thr_smooth.npy', thr_s); np.save('/work/clim_smooth.npy', clim_s)

sc = sea_mask
print("thr_smooth finite for sea cells:", np.isfinite(thr_s[:, sc]).all())
print("thr range (sea, smoothed):", np.nanmin(thr_s[:, sc]), np.nanmax(thr_s[:, sc]))

# ---- hot / MHW / events (recompute) ----
tgt = SST[nb:].reshape(len(tgt_dates), 3600)
doys = np.array([mdoy(d) for d in tgt_dates])
hot = (tgt >= thr_s[doys - 1]) & sea_mask[np.newaxis, :]
print("hot cell-days:", int(hot.sum()))

n_t = len(tgt_dates)
mhw = np.zeros((n_t, 3600), dtype=np.uint8)
for c in range(3600):
    h = hot[:, c]
    if not h.any(): continue
    i = 0
    while i < n_t:
        if h[i]:
            j = i
            while j < n_t and h[j]: j += 1
            if j - i >= 5:
                mhw[i:j, c] = 1
            i = j
        else:
            i += 1
# merge pass (iterate to stable)
changed = True
while changed:
    changed = False
    for c in range(3600):
        m = mhw[:, c]
        i = 0; runs = []
        while i < n_t:
            if m[i]:
                j = i
                while j < n_t and m[j]: j += 1
                runs.append((i, j-1)); i = j
            else: i += 1
        newruns = []
        for s, e in runs:
            if newruns and s - newruns[-1][1] - 1 <= 2:
                newruns[-1] = (newruns[-1][0], e); changed = True
            else:
                newruns.append((s, e))
        if len(newruns) != len(runs):
            m2 = np.zeros_like(m)
            for s, e in newruns: m2[s:e+1] = 1
            mhw[:, c] = m2
np.save('/work/mhw.npy', mhw)
print("MHW cell-days (incl. gap days):", int(mhw.sum()))

active = mhw.any(axis=1)
d = np.diff(np.concatenate([[0], active.view(np.int8), [0]]))
st = np.where(d == 1)[0]; en = np.where(d == -1)[0] - 1
ev = [(tgt_dates[s].isoformat(), tgt_dates[e].isoformat(), int(e - s + 1)) for s, e in zip(st, en)]
print("active days:", int(active.sum()), "regional events:", len(ev))
for e in ev: print("  ", e)
pickle.dump(ev, open('/work/events.pkl','wb'))
