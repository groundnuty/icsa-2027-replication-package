import numpy as np, json

X = np.load("/tmp/X.npy")          # (4028, 3600) 1991-12-27..2003-01-05
p3 = np.load("/tmp/p3.npy")        # (92, 3600)   2009-06-01..2009-08-31
sea = np.load("/tmp/sea.npy")      # (3600,)
nsea = int(sea.sum())

cand0 = np.datetime64("1991-12-27")
cand = cand0 + np.arange(X.shape[0])
b_start = np.datetime64("1992-01-01"); b_end = np.datetime64("2002-12-31")

def doy(dates):
    i = dates.astype("int64")
    yr = dates.astype("datetime64[Y]").astype("datetime64[D]").astype("int64")
    return (i - yr) + 1

cand_doy = doy(cand)
print("cand doy min/max:", cand_doy.min(), cand_doy.max(), "has 60:", bool((cand_doy == 60).any()))

M = np.zeros((366, X.shape[0]), dtype=bool)
for o in range(-5, 6):
    b = cand + np.timedelta64(o, "D")
    within = (b >= b_start) & (b <= b_end)
    k = np.where(within)[0]
    d = doy(b)[k]
    M[d, k] = True

poolsz = M.sum(axis=1)
print("pool sizes: min", poolsz.min(), "max", poolsz.max())
print("pool size for d=55,59,60,61:", poolsz[54], poolsz[58], poolsz[59], poolsz[60])
f29 = np.where(cand_doy == 60)[0]
for k in f29:
    print(cand[k], "in pools (doy):", (np.where(M[:, k])[0] + 1).tolist())

Xsea = X[:, sea]
thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
empty = 0
for d in range(1, 366):
    if d == 60: continue
    vals = Xsea[M[d-1]]
    nv = np.isfinite(vals)
    thr[d] = np.nanquantile(vals, 0.9, axis=0, method="hazen")
    clim[d] = np.nanmean(vals, axis=0)
    empty += int((~nv.any(axis=0)).sum())
print("cell-days with empty pool:", empty)
thr[60] = (thr[59] + thr[61]) / 2.0
clim[60] = (clim[59] + clim[61]) / 2.0
print("NaNs after fill: thr", int(np.isnan(thr).sum()), "clim", int(np.isnan(clim).sum()))

def smooth31(a):
    idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366
    return a[idx].mean(axis=2)
thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("smoothed thr NaNs:", int(np.isnan(thr_s).sum()))
print("sanity: thr_s d=183 (1 Jul) first 3:", thr_s[183, :3])
print("sanity: SST 2009-07-01 first 3 sea cells:", p3[31, sea][:3])

np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clim_s.npy", clim_s)
np.save("/tmp/cand_doy.npy", cand_doy)
print("OK")
