import numpy as np
rng = np.random.default_rng(0)
def hazen_nanperc(A, p=0.9):  # A shape (n, cells)
    n = A.shape[0]
    s = np.sort(A, axis=0)
    m = np.isnan(s).sum(axis=0)
    k = n - m
    out = np.full(A.shape[1:], np.nan)
    ok = k > 0
    if not ok.any(): return out
    kk = np.where(ok, k, 1)
    h = (kk - 1) * p + 1
    lo = (np.floor(h).astype(int) - 1); hi = (np.ceil(h).astype(int) - 1)
    lo = np.clip(lo, 0, kk - 1); hi = np.clip(hi, 0, kk - 1)
    idx = np.arange(A.shape[1])
    xlo = s[lo, idx]; xhi = s[hi, idx]
    frac = h - np.floor(h)
    res = xlo + frac * (xhi - xlo)
    out[ok] = res[ok]
    return out

A = rng.normal(10, 2, size=(137, 500))
mask = rng.random((137, 500)) < 0.3
A[mask] = np.nan
mine = hazen_nanperc(A)
ref = np.nanpercentile(A, 90, axis=0, method="hazen")
print("max abs diff vs numpy:", np.nanmax(np.abs(mine - ref)))
A[:, 0] = np.nan
print("all-nan col -> mine:", hazen_nanperc(A)[0], " numpy:", np.nanpercentile(A[:,0], 90, method="hazen"))
B = A[:, 5]; Bf = B[np.isfinite(B)]
print("quantile check:", np.quantile(Bf, 0.9, method="hazen"), np.nanpercentile(B, 90, method="hazen"), hazen_nanperc(A)[5])
# note: does np.nanpercentile promote to float64?
print("nanpercentile dtype:", ref.dtype)
