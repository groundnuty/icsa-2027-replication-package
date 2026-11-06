import numpy as np

X = np.load("/tmp/X.npy")
p3 = np.load("/tmp/p3.npy")
sea = np.load("/tmp/sea.npy")
nsea = int(sea.sum())

# Task mapping: doy = leap-year prefix of month + day (29 Feb = 60, 1 Mar = 61 always)
PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dt = dates.astype("datetime64[D]")
    m = dt.astype("datetime64[M]") // np.datetime64(1, "M")  # months since 1970-01
    m = (dt.astype("int64") // 1)  # days
    # extract month and day cleanly:
    dt64 = dt.astype("datetime64[D]")
    month = (dt64.astype("datetime64[M]") // np.datetime64(1, "M")).astype("int64") % 12
    day = dt64.astype("int64") - (dt64.astype("datetime64[M]").astype("int64"))
    return PREF[month] + day

# verify on known dates
for s, expect in [("1992-01-01",1),("1992-02-28",59),("1992-02-29",60),("1992-03-01",61),
                  ("1993-03-01",61),("1993-12-31",366),("2000-02-29",60),("2001-07-01",183),
                  ("1992-07-01",183)]:
    got = doy(np.array([s], dtype="datetime64[D]"))[0]
    assert got == expect, (s, got, expect)
print("doy mapping OK")

cand0 = np.datetime64("1991-12-27")
cand = cand0 + np.arange(X.shape[0])
b_start = np.datetime64("1992-01-01"); b_end = np.datetime64("2002-12-31")
cand_doy = doy(cand)
print("cand doy min/max:", cand_doy.min(), cand_doy.max(), "has 60:", bool((cand_doy==60).any()), "has 366:", bool((cand_doy==366).any()))

M = np.zeros((366, X.shape[0]), dtype=bool)   # row = doy-1
for o in range(-5, 6):
    b = cand + np.timedelta64(o, "D")
    within = (b >= b_start) & (b <= b_end)
    k = np.where(within)[0]
    M[doy(b)[k] - 1, k] = True

poolsz = M.sum(axis=1)
print("pool sizes: min", poolsz.min(), "max", poolsz.max(), " doy55,59,60,61:", poolsz[54], poolsz[58], poolsz[59], poolsz[60])
f29 = np.where(cand_doy == 60)[0]
print("1992-02-29 in pools:", (np.where(M[:, f29[0]])[0] + 1).tolist())
k1 = np.where(cand == np.datetime64("1993-03-01"))[0][0]
print("1993-03-01 in pools:", (np.where(M[:, k1])[0] + 1).tolist())

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
print("NaNs rows 1..365 after fill: thr", int(np.isnan(thr[1:]).sum()), "clim", int(np.isnan(clim[1:]).sum()))

def smooth31(a):
    idx = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366
    return a[idx].mean(axis=1)   # (366, 31, nsea) -> (366, nsea)
thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("thr_s shape:", thr_s.shape, " NaNs:", int(np.isnan(thr_s).sum()))
print("thr_s doy=183 (1 Jul) first 3 cells:", thr_s[183, :3])
print("SST 2009-07-01 first 3 sea cells:", p3[31, sea][:3])
print("thr_s range:", thr_s.min(), thr_s.max(), " clim_s range:", clim_s.min(), clim_s.max())

np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clim_s.npy", clim_s)
np.save("/tmp/cand_doy.npy", cand_doy)
np.save("/tmp/M.npy", M)
print("OK")
