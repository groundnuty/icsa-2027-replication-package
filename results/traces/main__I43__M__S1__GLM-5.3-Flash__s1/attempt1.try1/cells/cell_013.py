import numpy as np
from datetime import date

z = np.load('/work/cubes.npz')
base_cube = z['base_cube']
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1] + d.day)

sea_flat = np.load('/work/sea_flat.npy')
base_sea = base_cube.reshape(len(base_ds), -1)[:, sea_flat].astype('float64')  # (4028, 3308)
ords = np.array([d.toordinal() for d in base_ds])
base_doy = np.array([md_doy(d) for d in base_ds])

pools = {}
for dd in range(1, 367):
    if dd == 60: continue
    seed_ord = ords[base_doy == dd]
    pools[dd] = np.where((np.abs(ords[:, None] - seed_ord[None, :]) <= 5).any(axis=1))[0]

# --- manual type-5 (hazen) quantile check on random pools ---
def hazen_manual(x, p=0.9):
    x = np.sort(np.asarray(x, dtype='float64'))
    n = x.size
    h = n*p + 0.5
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    lo = min(max(lo, 1), n); hi = min(max(hi, 1), n)
    return x[lo-1] + (h - lo) * (x[hi-1] - x[lo-1]) if hi != lo else x[lo-1]

rng = np.random.default_rng(0)
ok = True
for _ in range(200):
    n = rng.integers(1, 200)
    x = rng.normal(size=n)
    x[rng.random(n) < 0.1] = np.nan
    if np.all(np.isnan(x)): continue
    a = np.nanquantile(x, 0.9, method='hazen')
    b = hazen_manual(x)
    if not np.isclose(a, b, rtol=0, atol=1e-12):
        ok = False; print('MISMATCH', n, a, b)
print('hazen manual vs numpy: all match:', ok)

# --- compute per-doy threshold & clim ---
nsea = base_sea.shape[1]
thr = np.full((366, nsea), np.nan)
clm = np.full((366, nsea), np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    vals = base_sea[pools[dd]]              # (n_pool, nsea)
    thr[dd-1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    clm[dd-1] = np.nanmean(vals, axis=0)
assert np.isfinite(thr).all() and np.isfinite(clm).all()
print('per-doy threshold/clim done; no NaN')

# day 60 = mean of days 59 and 61
thr[59] = 0.5*(thr[58] + thr[60])
clm[59] = 0.5*(clm[58] + clm[60])

# --- circular 31-day centred moving mean ---
def circ_smooth31(a):
    # a: (366, ...) indexed by doy-1; wrap over 366
    idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
    return a[idx].mean(axis=1)

# brute-force check
def brute(a):
    out = np.empty_like(a)
    for d in range(366):
        s = 0.0
        for off in range(-15, 16):
            s += a[(d + off) % 366]
        out[d] = s / 31.0
    return out
test = rng.normal(size=(366, 3))
print('smooth check max diff:', np.abs(circ_smooth31(test) - brute(test)).max())

thr_s = circ_smooth31(thr)
clm_s = circ_smooth31(clm)
np.savez_compressed('/work/clim.npz', thr_s=thr_s, clm_s=clm_s)
print('saved clim.npz')
# plausible?
print('cell 0 (doy 180): clim %.3f thr %.3f K | doy 15: clim %.3f thr %.3f K' %
      (clm_s[179,0], thr_s[179,0], clm_s[14,0], thr_s[14,0]))
print('region-mean summer clim (doy 200):', clm_s[199].mean(), 'thr:', thr_s[199].mean())
