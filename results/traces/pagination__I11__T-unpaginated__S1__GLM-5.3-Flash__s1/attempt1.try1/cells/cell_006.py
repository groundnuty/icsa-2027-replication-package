import numpy as np, time
rng = np.random.default_rng(0)
# probe hazen semantics on small samples
for n in [1,2,3,4,5,10,121]:
    x = np.arange(1, n+1, dtype=float)
    q = np.quantile(x, 0.9, method='hazen')
    q50 = np.quantile(x, 0.5, method='hazen')
    print(f'n={n:4d} q90={q:.6f} q50={q50:.6f}')
# check equivalence with manual: 0-based virtual index
def manual_hazen(x, p=0.9):
    xs = np.sort(x)  # NaNs last
    n = np.isfinite(xs).sum()
    v = p*n - 0.5
    lo = int(np.floor(v)); frac = v - lo
    lo = min(lo, n-1); hi = min(lo+1, n-1)
    return (1-frac)*xs[lo] + frac*xs[hi]
x = np.arange(1, 122, dtype=float)
print('n=121 exact-ish check:', np.quantile(x,0.9,method='hazen'), manual_hazen(x))
# random test with NaNs vs nanquantile
for trial in range(5):
    v = rng.normal(size=121); v[rng.random(121) < 0.2] = np.nan
    a = np.nanquantile(v, 0.9, method='hazen')
    b = manual_hazen(v)
    print('trial', trial, 'nanquantile', a, 'manual', b, 'match', np.isclose(a, b, equal_nan=True))
# speed test on pool-sized array
big = rng.normal(size=(121, 60*60))
big[rng.random(big.shape) < 0.15] = np.nan
t0=time.time(); r1 = np.nanquantile(big, 0.9, axis=0, method='hazen'); print('nanquantile 3600 cols: %.2f s' % (time.time()-t0))
t0=time.time(); r2 = np.nanmean(big, axis=0); print('nanmean: %.2f s' % (time.time()-t0))
print('shape', r1.shape)
