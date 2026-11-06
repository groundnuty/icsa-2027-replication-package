import numpy as np, pickle
from datetime import date, timedelta

thr2 = np.load("/work/thr_smooth2.npy")
thr1 = np.load("/work/thr_smooth.npy")
d = np.abs(thr2 - thr1)
print("max abs diff anywhere (all 366 doys):", np.nanmax(d))
i, j, k = np.unravel_index(np.nanargmax(d), d.shape)
print("at doy", i+1, "cell", j, k)

# also compare raw (pre-smoothing)
thr2_raw = None
# recompute raw for exact pools quickly? Check raw diff at edges
arr = np.load("/work/baseline_region_f32.npy")
data = arr.astype(np.float64)
with open("/work/pool_idx.pkl","rb") as f:
    pool_idx = pickle.load(f)
# d=1: exact pool = 1991-12-27..2002-01-06; old d=1 pool = 1992-01-01..2002-01-06
# compare thresholds for d=1 (index 0)
def thr_from_idx(ii):
    v = data[ii]
    s = np.sort(v, axis=0)
    nn = np.sum(~np.isnan(v), axis=0)
    with np.errstate(invalid="ignore"):
        h = nn*0.9 + 0.5
    h = np.where(nn>0, h, np.nan)
    lo = np.floor(h).astype(np.int64) - 1
    frac = h - np.floor(h)
    lo_c = np.clip(lo, 0, v.shape[0]-1); hi_c = np.clip(lo+1, 0, v.shape[0]-1)
    v_lo = np.take_along_axis(s, lo_c[None], axis=0)[0]
    v_hi = np.take_along_axis(s, hi_c[None], axis=0)[0]
    return v_lo + frac*(v_hi-v_lo), nn

ii_new = pool_idx[1]
k_of = lambda dt: (date(dt.year,dt.month,dt.day) - date(1991,12,27)).days
ii_old = [k_of(dt) for dt in [date(1992,1,1)+timedelta(days=kk) for kk in range(66)]]
# old d=1 pool: baseline dates with doy in [1..6] & !=60 -> Jan 1-6 each year (1992..2002) = 66
ii_old = []
dt = date(1992,1,1)
MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
for y in range(1992,2003):
    for dd in range(1,7):
        ii_old.append(k_of(date(y,1,dd)))
q_new, nn_new = thr_from_idx(np.array(ii_new))
q_old, nn_old = thr_from_idx(np.array(ii_old))
print("d=1 thr new (sample cell):", q_new[30,30], " old:", q_old[30,30])
print("d=1 pool sizes:", len(ii_new), len(ii_old))
