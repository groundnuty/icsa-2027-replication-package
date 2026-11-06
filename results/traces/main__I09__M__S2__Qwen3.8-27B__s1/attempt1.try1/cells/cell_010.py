import numpy as np
print(np.__version__)
rng = np.random.default_rng(0)

def my_hazen90(x):
    x = x[np.isfinite(x)]
    n = x.size
    if n == 0:
        return np.nan, np.nan
    s = np.sort(x)
    r = 0.9 * n
    f = int(min(np.floor(r), n-1)); c = int(min(np.ceil(r), n-1))
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
    q2 = np.quantile(x, 0.9, method='hazen')
    m2 = np.nanmean(x)
    if not (q1 == q2 or np.isclose(q1, q2, rtol=0, atol=1e-9)) or not np.isclose(m1, m2, rtol=0, atol=1e-9):
        ok = False
        print("MISMATCH", n, q1, q2, m1, m2)
        break
print("formula check:", "PASS" if ok else "FAIL")