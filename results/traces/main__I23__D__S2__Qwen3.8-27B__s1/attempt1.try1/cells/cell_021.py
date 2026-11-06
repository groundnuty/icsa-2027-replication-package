import numpy as np

# Hyndman-Fan type 5 (hazen): p_k = (k - 0.5)/n for k-th order statistic (1-indexed).
# Inverse (quantile): position k = p*n + 0.5 (1-indexed), linear interp, clamp to [1, n].
def hf_type5(x, p):
    xs = np.sort(x)
    n = len(xs)
    k = p*n + 0.5
    k = min(max(k, 1.0), float(n))
    lo = int(np.floor(k)); hi = min(lo+1, n)
    if lo == hi or lo >= n:
        return xs[min(int(round(k)), n) - 1]
    frac = k - lo
    return xs[lo-1] + frac*(xs[hi-1]-xs[lo-1])

rng = np.random.default_rng(1)
for n in (1,2,3,11,50,109,121,1000):
    xx = rng.normal(0,1,n)
    a = np.quantile(xx, 0.9, method='hazen')
    b = hf_type5(xx, 0.9)
    c = np.quantile(xx, 0.9, method='linear')
    print(n, "hazen %.6f  hf5 %.6f  match=%s  (linear would be %.6f)" % (a, b, np.isclose(a,b,atol=1e-12), c))
