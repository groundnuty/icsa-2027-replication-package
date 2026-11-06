import numpy as np
np.set_printoptions(precision=6, suppress=False)
col = np.array([1.0, np.nan, 2.0, 5.0, 3.0, 4.0])  # k=5 finite
def hazen_nanperc(A, p=0.9):
    n = A.shape[0]
    s = np.sort(A, axis=0)
    m = np.isnan(s).sum(axis=0)
    k = n - m
    kk = np.where(k>0, k, 1)
    h = (kk - 1) * p + 1
    lo = (np.floor(h).astype(int) - 1); hi = (np.ceil(h).astype(int) - 1)
    lo = np.clip(lo, 0, kk - 1); hi = np.clip(hi, 0, kk - 1)
    xlo = s[lo]; xhi = s[hi]
    frac = h - np.floor(h)
    return np.where(k>0, xlo + frac*(xhi-xlo), np.nan)
mine = hazen_nanperc(col)
ref = np.nanpercentile(col, 90, method="hazen")
print("sorted:", np.sort(col))
print("mine:", mine, "ref:", ref)
# manual: k=5, h=(5-1)*0.9+1=4.6 -> 1-based lo=4 hi=5 -> 0-based 3,4 -> x=3+0.6*(5-4)=3.6
sf = np.sort(col[np.isfinite(col)])
print("manual calc:", sf[3] + 0.6*(sf[4]-sf[3]))
# check np.quantile on finite values
print("np.quantile finite hazen:", np.quantile(sf, 0.9, method="hazen"))
# check what numpy nanpercentile does with method param — maybe it defaults differently
print("np.nanquantile:", np.nanquantile(col, 0.9, method="hazen"))
