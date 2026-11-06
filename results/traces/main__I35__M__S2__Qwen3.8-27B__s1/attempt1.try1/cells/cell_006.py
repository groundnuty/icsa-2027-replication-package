import numpy as np, json

X = np.load("/tmp/X.npy")          # (4028, 3600) 1991-12-27..2003-01-05
p3 = np.load("/tmp/p3.npy")        # (92, 3600)   2009-06-01..2009-08-31
sea = np.load("/tmp/sea.npy")      # (3600,)

cand0 = np.datetime64("1991-12-27")
cand = cand0 + np.arange(X.shape[0])
b_start = np.datetime64("1992-01-01"); b_end = np.datetime64("2002-12-31")

def doy(dates):
    # day of year 1..366 (Feb 29 = 60)
    yr = dates.astype("datetime64[Y]").astype(int) + 1970
    jan1 = np.datetime64(0, "D") + yr * np.timedelta64(0)  # placeholder
    jan1 = (yr.astype("datetime64[Y]").astype("int64"))
    # vectorized: days since Jan 1 of same year
    return ((dates.astype("int64") - (np.datetime64(0,"D")+ (yr-1970)  ).astype("int64")))  # wrong, redo below

# cleaner doy
def doy(dates):
    i = dates.astype("int64")                      # days since 1970-01-01
    yr = dates.astype("datetime64[Y]").astype("int64")   # days since epoch at Jan 1
    return (i - yr) + 1

cand_doy = doy(cand)
print("cand doy min/max:", cand_doy.min(), cand_doy.max(), "has 60:", np.isin(60, cand_doy).any())

# pool membership M[d, k] = cand[k] within +/-5 days of a baseline date with doy d
n = X.shape[0]
M = np.zeros((366, n), dtype=bool)
for o in range(-5, 6):
    b = cand + np.timedelta64(o, "D")
    within = (b >= b_start) & (b <= b_end)
    d = doy(b)
    k = np.where(within)[0]
    M[d[k], k] = True

poolsz = M.sum(axis=1)
print("pool sizes: min", poolsz.min(), "max", poolsz.max())
print("pool size for d=55,59,61:", poolsz[54], poolsz[58], poolsz[60])
print("day60 pool size (should be 0):", poolsz[59])
# check Feb29 dates belong to pools of calendar neighbours: which d contain each Feb 29 date?
f29 = np.where(cand_doy == 60)[0]
for k in f29:
    ds = np.where(M[:, k])[0] + 1
    print(cand[k], "belongs to pools (doy):", ds.tolist())

Xsea = X[:, sea]   # (4028, 3302)
thr = np.full((366, sea.sum()), np.nan)
clim = np.full((366, sea.sum()), np.nan)
empty = 0
for d in range(1, 366):
    if d == 60: continue
    idx = np.where(M[d-1])[0]
    vals = Xsea[idx]                      # (poolsize, nsea)
    nv = np.isfinite(vals)
    thr[d] = np.nanquantile(vals, 0.9, axis=0, method="hazen")
    clim[d] = np.nanmean(vals, axis=0)
    empty += int((~nv.any(axis=0)).sum())
print("cells with empty pool for some d:", empty)
thr[60] = (thr[59] + thr[61]) / 2.0
clim[60] = (clim[59] + clim[61]) / 2.0
print("NaN rows after fill: thr", np.isnan(thr).sum(), "clim", np.isnan(clim).sum())

# smooth: centred 31-day moving mean, wrap over 366
def smooth31(a):
    out = np.empty_like(a, dtype=np.float64)
    for d in range(366):
        idx = (d - 15 + np.arange(31)) % 366
        out[d] = a[idx].mean(axis=0)
    return out
thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("smoothed thr NaNs:", np.isnan(thr_s).sum())

np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clim_s.npy", clim_s)
np.save("/tmp/cand_doy.npy", cand_doy)
print("sample thr_s for d=183 (Jul 1) first 3 cells:", thr_s[183, :3])
print("sample SST 2009-07-01 first 3 sea cells:", p3[31, sea][:3])
