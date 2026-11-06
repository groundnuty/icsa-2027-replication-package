import numpy as np

def hazen_manual(x, p=0.9):
    x = np.asarray(x, dtype='float64')
    x = np.sort(x[np.isfinite(x)])   # ignore NaN, then sort
    n = x.size
    h = n*p + 0.5
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    lo = min(max(lo, 1), n); hi = min(max(hi, 1), n)
    return x[lo-1] if hi == lo else x[lo-1] + (h - lo) * (x[hi-1] - x[lo-1])

rng = np.random.default_rng(0)
ok = True; worst = 0.0
for _ in range(500):
    n = int(rng.integers(1, 300))
    x = rng.normal(size=n)
    x[rng.random(n) < 0.15] = np.nan
    if np.all(np.isnan(x)): continue
    a = np.nanquantile(x, 0.9, method='hazen')
    b = hazen_manual(x)
    worst = max(worst, abs(a-b))
    if not (a == b or np.isclose(a, b, rtol=0, atol=1e-13)):
        ok = False; print('MISMATCH', n, a, b)
print('hazen manual vs numpy: all match:', ok, '| worst abs diff:', worst)
# also test small n and no-NaN edge cases
for n in [1,2,3,5,10]:
    x = np.arange(1.0, n+1)
    print('n=%d p90:' % n, np.quantile(x, 0.9, method='hazen'), hazen_manual(x))
