import numpy as np
print("numpy", np.__version__)
# check nanquantile supports method
x = np.arange(1, 11, dtype=float)
print("nanquantile hazen:", np.nanquantile(x, 0.9, method='hazen'))
# manual HF type5: h1idx = n*p + 0.5
def hazen_manual(v, p):
    v = v[~np.isnan(v)]
    n = v.size
    if n == 0: return np.nan
    S = np.sort(v)
    h = min(max(n*p - 0.5, 0.0), n - 1)   # 0-indexed position
    lo = int(np.floor(h)); hi = int(np.ceil(h)); f = h - lo
    return S[lo]*(1-f) + S[hi]*f
for n in [1, 2, 4, 5, 10, 11, 120, 121, 122]:
    v = np.random.default_rng(n).uniform(0, 100, n)
    a = np.nanquantile(v, 0.9, method='hazen')
    b = hazen_manual(v, 0.9)
    print(f"n={n}: numpy={a!r} manual={b!r} match={np.isclose(a, b)}")
# with NaNs present
v = np.array([3.0, np.nan, 1.0, 2.0, 4.0])
print("with NaN: numpy", np.nanquantile(v, 0.9, method='hazen'), "manual", hazen_manual(v, 0.9))
