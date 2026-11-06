import numpy as np, datetime, time, warnings

t0 = time.time()
V_base = np.load('/work/V_base.npy').astype(np.float64)   # (4028, 60, 60)
V_tgt  = np.load('/work/V_tgt.npy').astype(np.float64)    # (92, 60, 60)
C = 60*60
B = V_base.reshape(4028, C)
T = V_tgt.reshape(92, C)

# ---- custom day-of-year mapping (leap-year calendar, Feb 29 = 60) ----
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
d = 0
for m in range(1,13):
    for dd in range(1, mdays[m-1]+1):
        d += 1
        doy_of[(m,dd)] = d
assert doy_of[(1,1)]==1 and doy_of[(2,28)]==59 and doy_of[(2,29)]==60
assert doy_of[(3,1)]==61 and doy_of[(12,31)]==366 and len(doy_of)==366

d0 = datetime.date(1991,12,27); N = 4028
# ---- pool membership matrix P[k, d] ----
P = np.zeros((N, 367), dtype=bool)
cur = datetime.date(1992,1,1); bl_end = datetime.date(2002,12,31)
n_marked = 0
while cur <= bl_end:
    d = doy_of[(cur.month, cur.day)]
    if d != 60:
        k0 = (cur - datetime.timedelta(days=5) - d0).days
        k1 = (cur + datetime.timedelta(days=5) - d0).days
        assert k0 >= 0 and k1 < N, (cur, k0, k1)
        P[k0:k1+1, d] = True
        n_marked += 1
    cur += datetime.timedelta(days=1)
print("baseline dates marked:", n_marked, "(expect 4018-3=4015)")
poolsz = P.sum(axis=0)
print("pool sizes: min", poolsz[1:367].min(), "max", poolsz[1:367].max(),
      "non60 all 121:", np.all(poolsz[1:60]==121) and np.all(poolsz[61:367]==121),
      "d60:", poolsz[60])

# ---- thresholds & climatology ----
thr = np.full((367, C), np.nan); clim = np.full((367, C), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60: continue
        pool = B[np.flatnonzero(P[:, d])]          # (121, 3600)
        thr[d] = np.nanquantile(pool, 0.9, method="hazen", axis=0)
        clim[d] = np.nanmean(pool, axis=0)
print("pools done", time.time()-t0)

thr[60] = 0.5*(thr[59]+thr[61]); clim[60] = 0.5*(clim[59]+clim[61])

# ---- 31-day centred moving mean, wrap-around (day d = mean of d-15..d+15 mod 366) ----
def smooth31(x):
    # x: (366, C), rows doy 1..366
    xp = np.vstack([np.zeros((1, C)), np.concatenate([x, x, x], axis=0)])
    c = np.cumsum(xp, axis=0)
    i = np.arange(366)
    a = 366 + i - 15          # first row (0-based) in the tripled block
    b = 366 + i + 15
    return (c[b+1] - c[a]) / 31.0

thr366 = thr[1:367]; clim366 = clim[1:367]
thr_sm = smooth31(thr366); clim_sm = smooth31(clim366)

# sanity: smoothing == explicit mean for a few cells
x = thr366.copy()
c_ = 1234
for dd in [1, 15, 60, 153, 244, 350, 366]:
    idxs = [((dd-1) - j) % 366 for j in range(15, -16, -1)]
    assert np.isclose(thr_sm[dd-1, c_], x[idxs, c_].mean()), dd
print("smoothing verified at sample days")

# ---- target period ----
tgt_dates = [datetime.date(2009,6,1) + datetime.timedelta(days=k) for k in range(92)]
doys = np.array([doy_of[(dt.month, dt.day)] for dt in tgt_dates])
print("target doys:", doys.min(), doys.max(), "n:", len(doys), "unique:", len(set(doys.tolist())))
sea = np.isfinite(V_tgt).all(axis=0)
print("sea cells:", sea.sum(), "of", C)
# check the 3308 finite-per-day set is exactly the sea set
perday_fin = np.isfinite(V_tgt)
print("same finite set each day:", np.all(perday_fin == perday_fin[0:1]))

np.save('/work/thr_sm.npy', thr_sm); np.save('/work/clim_sm.npy', clim_sm)
np.save('/work/doys.npy', doys); np.save('/work/sea.npy', sea)
print("total", time.time()-t0)
