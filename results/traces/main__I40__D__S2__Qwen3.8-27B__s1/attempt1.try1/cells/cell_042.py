import numpy as np, datetime
V_base = np.load('/work/V_base.npy').astype(np.float64)
B = V_base.reshape(4028, 3600)
thr_sm = np.load('/work/thr_sm.npy')
d0 = datetime.date(1991,12,27)
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
d = 0
for m in range(1,13):
    for dd in range(1, mdays[m-1]+1):
        d += 1; doy_of[(m,dd)] = d
P = np.zeros((4028, 367), dtype=bool)
cur = datetime.date(1992,1,1)
while cur <= datetime.date(2002,12,31):
    dd = doy_of[(cur.month, cur.day)]
    if dd != 60:
        k0 = (cur - datetime.timedelta(days=5) - d0).days
        k1 = (cur + datetime.timedelta(days=5) - d0).days
        P[k0:k1+1, dd] = True
    cur += datetime.timedelta(days=1)

c = 1000
rows = np.flatnonzero(P[:, 153])
print("rows:", rows.min(), rows.max(), rows.size)
pool = B[rows, c]
print("pool finite:", np.isfinite(pool).sum(), "sorted head/tail:", np.sort(pool)[:3], np.sort(pool)[-3:])
q_vec = np.nanquantile(B[rows], 0.9, method="hazen", axis=0)[c]
print("vectorized q90 (this run):", q_vec)

# recompute FULL pipeline threshold column for cell 1000 exactly as pipeline did, all days
thr = np.full((367, 3600), np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    thr[dd] = np.nanquantile(B[np.flatnonzero(P[:, dd])], 0.9, method="hazen", axis=0)
thr[60] = 0.5*(thr[59]+thr[61])
# smooth exactly as pipeline
C = 3600
def smooth31(x):
    xp = np.vstack([np.zeros((1, C)), np.concatenate([x, x, x], axis=0)])
    cs = np.cumsum(xp, axis=0)
    i = np.arange(366)
    a = 366 + i - 15
    b = 366 + i + 15
    return (cs[b+1] - cs[a]) / 31.0
thr_sm_new = smooth31(thr[1:367])
print("recomputed thr_sm[152, 1000]:", thr_sm_new[152, c], " saved:", thr_sm[152, c])
print("equal saved vs recomputed overall:", np.allclose(thr_sm, thr_sm_new, equal_nan=True))
diff = np.abs(thr_sm - thr_sm_new)
print("max abs diff:", np.nanmax(diff))
