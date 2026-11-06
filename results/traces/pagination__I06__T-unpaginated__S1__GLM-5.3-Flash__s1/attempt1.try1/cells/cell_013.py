import numpy as np, datetime as dt, pickle, time, warnings

base_sst = np.load('/tmp/base_sst.npy')
with open('/tmp/meta.pkl','rb') as f:
    meta = pickle.load(f)
base_dates = [dt.date.fromisoformat(s) for s in meta['base_dates']]

def doy366(d):
    if d.month == 2 and d.day == 29:
        return 60
    if d.month <= 2:
        return (d - dt.date(d.year,1,1)).days + 1
    return 61 + (d - dt.date(d.year,3,1)).days

B0, B1 = dt.date(1992,1,1), dt.date(2002,12,31)
pool_idx = {}
for xi, X in enumerate(base_dates):
    for off in range(-5, 6):
        B = X + dt.timedelta(days=off)
        if B0 <= B <= B1:
            d = doy366(B)
            if d != 60:
                pool_idx.setdefault(d, []).append(xi)

# ---- validate hazen percentile against manual implementation ----
rng = np.random.default_rng(1)
def hazen_manual(x, p=0.9):
    v = np.sort(x[~np.isnan(x)])
    n = v.size
    if n == 0: return np.nan
    h = p*n + 0.5           # Hyndman-Fan type 5, 1-based virtual index
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    lo = min(max(lo,1),n); hi = min(max(hi,1),n)
    r = h - lo
    return v[lo-1] + r*(v[hi-1]-v[lo-1])
errs = []
for _ in range(200):
    n = rng.integers(5, 200)
    x = rng.normal(size=n)
    if rng.random() < 0.5: x[rng.integers(0,n, size=rng.integers(1,5))] = np.nan
    errs.append(abs(hazen_manual(x) - np.percentile(x, 90, method='hazen')))
print("hazen manual-vs-numpy max err:", max(errs))
# n=121 case check
x = np.sort(rng.normal(size=121))
print("n=121 h:", 0.9*121+0.5, "numpy:", np.percentile(x, 90, method='hazen'),
      "manual:", hazen_manual(x), "match:", abs(np.percentile(x,90,method='hazen')-hazen_manual(x))<1e-12)

# ---- validate moving mean against brute force on random data ----
def movmean31_circ(a):
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)        # len 396
    c = np.cumsum(ap, axis=0)
    cp = np.concatenate([np.zeros((1,)+a.shape[1:]), c], axis=0)  # len 397, cp[0]=0
    return (cp[31:] - cp[:-31]) / 31.0                        # out[j]=sum(ap[j..j+30])
def brute(a):
    return np.stack([np.stack([a[(j+k) % 366] for k in range(-15,16)]).mean(axis=0) for j in range(366)])
ra = rng.random((366, 3, 2))
mm = movmean31_circ(ra); bb = brute(ra)
print("movmean-vs-brute max abs diff:", np.abs(mm-bb).max())
# also numpy-style padded roll check
rr = sum(np.roll(ra, -k, axis=0) for k in range(-15,16))/31.0
print("movmean-vs-rollsum max abs diff:", np.abs(mm-rr).max())

# ---- compute per-cell pools stats ----
bs64 = base_sst.astype(np.float64)
t0=time.time()
thr_raw = np.full((367, 60, 60), np.nan)   # day d at index d
clim_raw = np.full((367, 60, 60), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        block = bs64[pool_idx[d]]
        thr_raw[d] = np.nanpercentile(block, 90, axis=0, method='hazen')
        clim_raw[d] = np.nanmean(block, axis=0)
print("pool stats sec:", round(time.time()-t0,1))

thr_raw[60] = 0.5*(thr_raw[59] + thr_raw[61])
clim_raw[60] = 0.5*(clim_raw[59] + clim_raw[61])

targ_sst = np.load('/tmp/targ_sst.npy')
sea = np.isfinite(targ_sst.astype(np.float64)).all(axis=0)
print("finite on sea cells (raw):", np.isfinite(thr_raw[1:]).all(axis=(1,2)).all() or "some NaN",
      "| sea-only thr:", np.isfinite(thr_raw[1:][:, sea]).all(), "clim:", np.isfinite(clim_raw[1:][:, sea]).all())
print("NaN only on land:", np.isfinite(thr_raw[1:]).sum(axis=0)[~sea].max() == 0 if (~sea).any() else "no land",
      "-> nonfinite land cells:", int((~np.isfinite(thr_raw[100])).sum() - (~sea).sum()))

t366 = thr_raw[1:]; c366 = clim_raw[1:]
thr = movmean31_circ(t366)   # entry j = smoothed day j+1
clim = movmean31_circ(c366)
# verify vs brute force on the real fields for several days
for d in [1, 2, 60, 61, 153, 154, 244, 365, 366]:
    idxs = [(d-1+k) % 366 for k in range(-15,16)]
    assert np.allclose(t366[idxs].mean(axis=0), thr[d-1], rtol=0, atol=1e-12), d
    assert np.allclose(c366[idxs].mean(axis=0), clim[d-1], rtol=0, atol=1e-12), d
print("thr/clim movmean verified vs brute force")
print("thr finite on sea:", np.isfinite(thr[:, sea]).all(), " clim finite on sea:", np.isfinite(clim[:, sea]).all())
print("thr sample (cell 30,30): doy152-156:", np.round(thr[151:156, 30, 30], 4))
print("clim sample (cell 30,30): doy152-156:", np.round(clim[151:156, 30, 30], 4))
print("thr range:", thr.min(), thr.max(), "clim range:", clim.min(), clim.max())

np.save('/tmp/thr.npy', thr)      # entry j = day j+1
np.save('/tmp/clim.npy', clim)
with open('/tmp/pools.pkl','wb') as f:
    pickle.dump({str(k): v for k, v in pool_idx.items()}, f)
print("saved thr, clim, pools")
