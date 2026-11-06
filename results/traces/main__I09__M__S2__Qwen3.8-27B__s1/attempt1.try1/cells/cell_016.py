import numpy as np
d = np.load("cache/region.npz")
sst_b = d['sst_base']; tb = d['time_base']
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(s):
    return CUM[int(s[5:7])-1] + int(s[8:10])
doy_b = np.array([doy(s) for s in tb], dtype=int)
is_baseline = (tb >= "1992-01-01") & (tb <= "2002-12-31")
N = len(tb)
mask = np.zeros(N, dtype=bool)
for i in np.where(is_baseline & (doy_b == 1))[0]:
    mask[max(i-5,0):min(i+5,N-1)+1] = True
idx = np.flatnonzero(mask)
print("doy1 idx:", idx[:13], "count:", len(idx))
V = sst_b[idx, 0, 0]
print("cell (0,0) values for doy1 pool:", V[:13])
print("finite count:", np.isfinite(V).sum())
# check overall finiteness of sst_b in first 100 days
print("finite frac first 100 days:", np.isfinite(sst_b[:100]).mean())
print("sample:", sst_b[0,0,:5], sst_b[100,0,:5])