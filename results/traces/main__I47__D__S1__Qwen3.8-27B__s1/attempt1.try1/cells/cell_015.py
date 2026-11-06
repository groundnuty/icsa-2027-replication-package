import numpy as np, time, datetime as dt
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']; S_tgt = data['S_tgt']
sea = np.isfinite(S_tgt).all(axis=0)
Sb = S_base[:, sea].astype(np.float64)
n_sea = sea.sum()
pools = np.load('/work/pools.npy', allow_pickle=True).item()

t0 = time.time()
THR = np.full((366, n_sea), np.nan)
CLIM = np.full((366, n_sea), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = Sb[pools[d], :]
    valid = ~np.isnan(vals)
    n_valid = valid.sum(axis=0)
    s = np.where(valid, vals, 0.0).sum(axis=0)
    CLIM[d-1] = np.where(n_valid > 0, s / np.where(n_valid>0, n_valid, 1), np.nan)
    sv = np.sort(vals, axis=0)
    n = n_valid.astype(np.float64)
    # Hazen / Hyndman-Fan type 5: 1-indexed k = n*p + 1/2 -> 0-indexed position = n*p - 1/2
    p0 = n * 0.9 - 0.5
    lo = np.floor(p0).astype(int)
    lo = np.clip(lo, 0, 120)
    lo = np.minimum(lo, np.maximum(n_valid - 1, 0))
    frac = p0 - lo.astype(np.float64)
    hi = np.clip(lo + 1, 0, 120)
    hi = np.minimum(hi, np.maximum(n_valid - 1, 0))
    idx = np.arange(n_sea)
    a = sv[lo, idx]
    b = sv[hi, idx]
    thr = (1.0 - frac) * a + frac * b
    THR[d-1] = np.where(n_valid > 0, thr, np.nan)
print("loop done", time.time()-t0)
THR[59] = 0.5*(THR[58] + THR[60])
CLIM[59] = 0.5*(CLIM[58] + CLIM[60])

rng = np.random.default_rng(1)
ok = True
for it in range(200):
    c = int(rng.integers(n_sea)); d = int(rng.integers(1, 367))
    if d == 60: continue
    v = Sb[pools[d], c]; v = v[~np.isnan(v)]
    ref = np.quantile(v, 0.9, method='hazen')
    if not np.allclose(ref, THR[d-1, c], rtol=1e-12, atol=1e-9):
        ok = False; print("THR MISMATCH", c, d, ref, THR[d-1, c])
print("hazen verification over 200 samples:", ok)
# exhaustive check on a few doys
for d in (1, 59, 61, 153, 244, 366):
    ref = np.quantile(np.sort(Sb[pools[d], :].reshape(-1, 3655))[:, :n_sea], 0.9, method='hazen', axis=0) if False else None
    okd = all(np.allclose(np.quantile(Sb[pools[d], c][~np.isnan(Sb[pools[d], c])], 0.9, method='hazen'), THR[d-1, c]) for c in range(0, n_sea, 137))
    print(d, "ok:", okd)
np.savez_compressed('/work/thrclim.npz', THR=THR, CLIM=CLIM)
print("saved")
