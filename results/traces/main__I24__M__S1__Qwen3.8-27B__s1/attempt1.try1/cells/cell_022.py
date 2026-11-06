import numpy as np
print(np.__version__)
rng = np.random.default_rng(1)
x = rng.random((121, 5000))
x[rng.random((121,5000)) < 0.1] = np.nan
# compare nanquantile method='hazen' vs manual on non-nan
try:
    r = np.nanquantile(x, 0.9, axis=0, method="hazen")
    print("nanquantile method=hazen OK")
    # manual check for a few columns
    for c in [0, 100, 4999]:
        v = x[:, c]
        v = v[~np.isnan(v)]
        manual = np.quantile(v, 0.9, method="hazen")
        print(c, r[c], manual, np.isclose(r[c], manual))
except TypeError as e:
    print("no method param:", e)
    r = np.nanquantile(x, 0.9, axis=0, interpolation="hazen")
    print("interpolation param works")
