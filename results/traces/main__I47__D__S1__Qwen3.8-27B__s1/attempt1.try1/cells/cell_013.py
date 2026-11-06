import numpy as np, time, datetime as dt
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']; S_tgt = data['S_tgt']
dates = [dt.date.fromisoformat(s) for s in data['dates']]
sea = np.isfinite(S_tgt).all(axis=0)
Sb = S_base[:, sea].astype(np.float64)
n_sea = sea.sum()
pools = np.load('/work/pools.npy', allow_pickle=True).item()

t0 = time.time()
THR = np.full((366, n_sea), np.nan)
CLIM = np.full((366, n_sea), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = Sb[pools[d], :]                      # (121, n_sea)
    valid = ~np.isnan(vals)
    n_valid = valid.sum(axis=0)
    s = np.where(valid, vals, 0.0).sum(axis=0)
    clim = np.where(n_valid > 0, s / np.where(n_valid>0, n_valid, 1), np.nan)
    CLIM[d-1] = clim
    sv = np.sort(vals, axis=0)                  # NaNs at the end
    n = n_valid.astype(np.float64)
    p = (n - 1.0) * 0.9
    lo = np.floor(p).astype(int)
    frac = p - lo
    lo = np.clip(lo, 0, 120)
    hi = np.clip(lo + 1, 0, 120)
    a = sv[lo, np.arange(n_sea)]
    b = sv[hi, np.arange(n_sea)]
    thr = (1.0 - frac) * a + frac * b
    thr = np.where(n > 0, thr, np.nan)
    THR[d-1] = thr
print("loop done", time.time()-t0)
THR[59] = 0.5*(THR[58] + THR[60])
CLIM[59] = 0.5*(CLIM[58] + CLIM[60])

rng = np.random.default_rng(0)
ok = True
for it in range(50):
    c = int(rng.integers(n_sea)); d = int(rng.integers(1, 367))
    if d == 60: continue
    v = Sb[pools[d], c]; v = v[~np.isnan(v)]
    ref = np.quantile(v, 0.9, method='hazen')
    if not np.allclose(ref, THR[d-1, c], rtol=1e-12, atol=1e-9):
        ok = False; print("THR MISMATCH", c, d, ref, THR[d-1, c])
    refm = np.nanmean(v)
    if not np.allclose(refm, CLIM[d-1, c], rtol=1e-12, atol=1e-9):
        ok = False; print("CLIM MISMATCH", c, d, refm, CLIM[d-1, c])
print("hazen/clim verification:", ok)
print("thr finite:", np.isfinite(THR).sum(), "/", THR.size, " clim finite:", np.isfinite(CLIM).sum())
np.savez_compressed('/work/thrclim.npz', THR=THR, CLIM=CLIM)
# smooth later; quick stats for target-window days
print("example thr day153 (2019-06-01 doy) first 5:", THR[152, :5])
