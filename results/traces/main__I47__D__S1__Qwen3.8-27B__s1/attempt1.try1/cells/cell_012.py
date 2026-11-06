import numpy as np, time
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']; S_tgt = data['S_tgt']
dates = [d for d in data['dates']]
import datetime as dt
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
    n_valid = valid.sum(axis=0)                 # per cell
    s = np.where(valid, vals, 0.0).sum(axis=0)
    with np.errstate(invalid='ignore'):
        clim = np.where(n_valid > 0, s / np.where(n_valid>0, n_valid, 1), np.nan)
    CLIM[d-1] = clim
    sv = np.sort(vals, axis=0)                  # NaNs go to the end
    # hazen: 1-based h = (n-1)*0.9 + 1  -> 0-based position p = (n-1)*0.9
    n = n_valid.astype(np.float64)
    p = (n - 1.0) * 0.9
    lo = np.floor(p).astype(int)
    frac = p - lo
    lo = np.clip(lo, 0, 120)
    hi = np.clip(lo + 1, 0, 120)
    a = sv[lo, np.arange(n_sea)]
    b = sv[hi, np.arange(n_sea)]
    thr = (1.0 - frac) * a + frac * b
    thr = np.where((n > 0) & (lo < n) , thr, np.nan)   # if n>=1 then lo <= n-1 always; guard anyway
    # if n==1: p=0, lo=0, frac=0 -> a=sv[0] fine; guard: lo < n ensures lo index is within valid part
    THR[d-1] = thr
print("loop done", time.time()-t0)

# day 60 = mean of 59 and 61
THR[59] = 0.5*(THR[58] + THR[60])
CLIM[59] = 0.5*(CLIM[58] + CLIM[60])

# verify against numpy quantile for a sample of cells
rng = np.random.default_rng(0)
import numpy.quantile as _q
ok = True
for it in range(30):
    c = rng.integers(n_sea); d = int(rng.integers(1, 367))
    if d == 60: continue
    v = Sb[pools[d], c]
    v = v[~np.isnan(v)]
    ref = np.quantile(v, 0.9, method='hazen')
    mine = THR[d-1, c]
    if not np.allclose(ref, mine, rtol=1e-12, atol=1e-9):
        ok = False; print("MISMATCH", c, d, ref, mine)
    refm = np.nanmean(Sb[pools[d], c]); mine_m = CLIM[d-1, c]
    if not np.allclose(refm, mine_m, rtol=1e-12, atol=1e-9):
        ok = False; print("CLIM MISMATCH", c, d, refm, mine_m)
print("hazen/clim verification:", ok)
print("thr finite:", np.isfinite(THR).sum(), "/", THR.size, " clim finite:", np.isfinite(CLIM).sum())
np.savez_compressed('/work/thrclim.npz', THR=THR, CLIM=CLIM)
print("THR range (Jun-Aug days 152..244):", np.nanmin(THR[151:245].min()), np.nanmax(THR[151:245].max()))
