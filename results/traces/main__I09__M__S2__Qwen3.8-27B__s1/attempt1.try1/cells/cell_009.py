import numpy as np
rng = np.random.default_rng(0)

def my_hazen90(x):  # x: 1d with possible NaN, returns (q90, mean)
    x = x[np.isfinite(x)]
    n = x.size
    if n == 0:
        return np.nan, np.nan
    s = np.sort(x)
    r = 0.9 * n          # hazen (HF type 5): 0-based position
    f = np.floor(r)
    c = np.ceil(r)
    f = min(int(f), n-1); c = min(int(c), n-1)
    q = s[f] + (r - f) * (s[c] - s[f])
    return q, x.mean()

ok = True
for trial in range(3000):
    n = int(rng.integers(1, 300))
    x = rng.normal(290, 3, n)
    m = rng.random(n) < 0.08
    x = np.where(m, np.nan, x)
    if not np.isfinite(x).any():
        continue
    q1, m1 = my_hazen90(x)
    q2 = np.quantile(x, 0.9, method='hazen', nan_policy='omit')
    m2 = np.nanmean(x)
    if not (np.isclose(q1, q2, rtol=0, atol=1e-9) and np.isclose(m1, m2, rtol=0, atol=1e-9)):
        ok = False
        print("MISMATCH", n, q1, q2)
        break
print("formula check:", "PASS" if ok else "FAIL")