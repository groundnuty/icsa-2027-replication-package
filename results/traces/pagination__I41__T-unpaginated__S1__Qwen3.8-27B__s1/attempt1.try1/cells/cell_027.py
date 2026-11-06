import numpy as np
# 1) verify numpy hazen formula h0 = n*q - 0.5 on several (n, q)
rng = np.random.default_rng(1)
ok = True
for trial in range(30):
    n = int(rng.integers(3, 500))
    q = float(rng.uniform(0.05, 0.99))
    x = np.sort(rng.normal(0, 1, n))
    got = np.quantile(x, q, method="hazen")
    h0 = min(max(n*q - 0.5, 0.0), n-1)
    lo = int(h0); site_g = h0-lo
    exp = x[lo] + (x[lo+1]-x[lo])*site_g if lo+1 < n else x[lo]
    if abs(got-exp) > 1e-12:
        ok = False
        print("MISMATCH n=%d q=%.4f got=%.12f exp=%.12f" % (n, q, got, exp))
print("formula h0 = n*q - 0.5 verified on 30 random cases:", ok)
# also compare with 'linear' (MATLAB default) to show difference
x = np.sort(rng.normal(0,1,121))
print("hazen vs linear on n=121: hazen=%.6f linear=%.6f (diff %.4f)" % (
    np.quantile(x,0.9,method='hazen'), np.quantile(x,0.9,method='linear'),
    np.quantile(x,0.9,method='hazen')-np.quantile(x,0.9,method='linear')))
