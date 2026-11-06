import numpy as np
rng = np.random.default_rng(0)
for n in (1,2,11,109,121):
    xx = np.sort(rng.normal(0,1,n))
    a = np.quantile(xx, 0.9, method='hazen')
    h = 1 + 0.9*(n-1)
    lo = int(np.floor(h)); hi = min(lo+1, n-1)
    b = xx[lo-1] + (h-lo)*(xx[hi]-xx[lo-1])
    print(n, a, b, np.isclose(a,b,atol=1e-12), "h=", h)
