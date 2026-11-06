import numpy as np
rng = np.random.default_rng(0)
def hazen_nanperc(A, p=0.9):  # A shape (n, cells), type 5: h = n*p + 0.5 (1-based)
    n = A.shape[0]
    s = np.sort(A, axis=0)
    m = np.isnan(s).sum(axis=0)
    k = n - m
    out = np.full(A.shape[1:], np.nan)
    ok = k > 0
    if not ok.any(): return out
    kk = np.where(ok, k, 1).astype(float)
    h = kk * p + 0.5                     # 1-based position
    j = np.floor(h).astype(int)          # 1-based lower index
    g = h - j
    j0 = np.clip(j, 1, kk.astype(int)) - 1
    jp = np.clip(j + 1, 1, kk.astype(int)) - 1
    idx = np.arange(A.shape[1])
    xlo = s[j0, idx]; xhi = s[jp, idx]
    res = xlo + g * (xhi - xlo)
    out[ok] = res[ok]
    return out

A = rng.normal(10, 2, size=(137, 800))
mask = rng.random((137, 800)) < 0.3
A[mask] = np.nan
mine = hazen_nanperc(A)
ref = np.nanpercentile(A, 90, axis=0, method="hazen")
print("max abs diff vs numpy hazen:", np.nanmax(np.abs(mine - ref)))
# extreme small-n pools
for n in range(1, 8):
    col = np.arange(1.0, n+1)
    print(n, col, "mine:", hazen_nanperc(col.reshape(-1,1))[0], "np:", np.nanpercentile(col, 90, method="hazen"))
# all-nan col
A2 = np.full((10,1), np.nan)
print("all-nan:", hazen_nanperc(A2)[0])
