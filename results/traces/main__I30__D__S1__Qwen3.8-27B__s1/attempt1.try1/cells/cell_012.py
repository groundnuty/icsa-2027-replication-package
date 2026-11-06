import numpy as np
# replicate the exact snippet on a synthetic all-NaN column
pool = np.full((121, 60, 60), np.nan)
pool[:, 30, 30] = np.linspace(280, 290, 121)
allnan = np.all(np.isnan(pool), axis=0)
psafe = np.where(allnan, 0.0, pool)
s = np.nansum(psafe, axis=0); c = np.count_nonzero(~allnan, axis=0)
out = np.where(c > 0, s / np.maximum(c, 1), np.nan)
print("synthetic: land cell out =", out[5,5], " sea cell out =", out[30,30])

# now check what the saved array really holds, and recompute for one d
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
d2i = {d: i for i, d in enumerate(dates)}
ext = A[:d2i['2003-01-05']+1]
print("A[0,22,4] (1991-12-27):", A[0,22,4])
print("A[1000,22,4]:", A[1000,22,4])
print("A[4000,22,4]:", A[4000,22,4])
col_nan = np.all(np.isnan(ext[:,22,4]))
print("cell (22,4) all NaN in ext:", col_nan)
