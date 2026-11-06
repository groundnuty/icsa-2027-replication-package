import numpy as np
rng = np.random.default_rng(0)

def hazen_manual(x, p):
    # Hyndman-Fan type 5, 1-based, x sorted ascending finite
    n = len(x)
    if n == 0: return np.nan
    h = (n+1)*p
    # numpy's actual behavior to be verified
    j = int(np.floor(h))
    frac = h - j
    if j >= n:  # extrapolation region
        # see numpy behavior
        return np.nan
    if frac == 0 or j+1 > n:
        return x[j-1] if j >= 1 else x[0]
    return x[j-1] + frac*(x[j]-x[j-1])

for n in [1,2,3,5,9,10,11,20,121]:
    x = np.sort(rng.normal(288, 2, n))
    a = np.quantile(x, 0.9, method='hazen')
    print(n, "numpy=%.10f  manual=%.10f" % (a, hazen_manual(x, 0.9)), "match:", np.isclose(a, hazen_manual(x,0.9)))
