import numpy as np
# reverse-engineer numpy hazen vs type-5 (h = n*q + 0.5, 1-based)
def type5(x, q):
    x = np.sort(np.asarray(x, float))
    n = x.size
    if n == 0: return np.nan
    h = n*q + 0.5
    if h <= 1: return float(x[0])
    if h >= n and h < n+1 and h != n:
        # beyond last plotting position -> clamp (verify vs numpy below)
        return float(x[-1])
    lo = int(np.floor(min(h, n))); hi = int(np.ceil(min(h, n)))
    if lo == hi: return float(x[lo-1])
    return float(x[lo-1] + (h-lo)*(x[hi-1]-x[lo-1]))

rng = np.random.default_rng(1)
bad = 0
for trial in range(3000):
    n = rng.integers(1, 60)
    x = rng.normal(size=n)*10 + 280
    q = float(rng.choice([0.9, 0.5, 0.1, 0.95, 0.25, 0.99]))
    a = np.quantile(x, q, method="hazen")
    b = type5(x, q)
    if not np.isclose(a, b, rtol=0, atol=1e-12):
        bad += 1
        if bad < 8: print("DIFF n=%d q=%.2f numpy=%.10f type5=%.10f" % (n, q, a, b))
print("mismatches:", bad, "of 3000")
# specific checks
print("numpy [1..5] q=.9:", np.quantile(np.arange(1,6.), .9, method="hazen"), "| type5:", type5(np.arange(1,6.), .9))
print("numpy [1..5] q=.5:", np.quantile(np.arange(1,6.), .5, method="hazen"))
print("numpy [1..4] q=.9:", np.quantile(np.arange(1,5.), .9, method="hazen"), "| type5:", type5(np.arange(1,5.), .9))
print("numpy [1..2] q=.9:", np.quantile(np.arange(1,3.), .9, method="hazen"), "| type5:", type5(np.arange(1,3.), .9))
print("MATLAB doc check quantile(1:5,0.9) -> should equal MATLAB 5.0 (type 5), NOT 4.6 (type 7)")
