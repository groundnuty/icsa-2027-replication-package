import numpy as np, time
arr = np.load("/work/baseline_region_f32.npy")
data = arr.astype(np.float64)  # (4028, 60, 60)
t0 = time.time()
# pool per cell and doy: for each doy d (excluding 60), collect values from win_dates[d] indices
import pickle
with open("/work/window_dates.pkl","rb") as f:
    wd = pickle.load(f)
win = wd["win_dates"]
# map date strings? win contains date objects; we need indices into data array which is in date order (1991-12-27..2003-01-05)
from datetime import date, timedelta
d0 = date(1991,12,27)
idx_of = {}
for k in range(data.shape[0]):
    idx_of[d0 + timedelta(days=k)] = k

pools = {}
t0 = time.time()
for dd, dates in win.items():
    ii = np.array([idx_of[dt] for dt in dates])
    vals = data[ii]  # (n, 60, 60)
    pools[dd] = vals
print("pooling time:", round(time.time()-t0,1), "s")
# quick check pool size for d=167
print("pool d=167:", pools[167].shape, "d=1:", pools[1].shape)
np.save("/work/pools.npy", np.array([0]))  # placeholder not saving pools (big)
# compute threshold (hazen 90th pct) and clim (mean) per cell/doy
NT = 366
thr = np.full((NT, 60, 60), np.nan)
clim = np.full((NT, 60, 60), np.nan)
t0 = time.time()
for dd in range(1, 367):
    if dd == 60: continue
    v = pools[dd]  # (n, 60, 60)
    clim[dd-1] = np.nanmean(v, axis=0)
    # hazen 90th percentile per cell: sort along axis 0
    s = np.sort(v, axis=0)
    n = v.shape[0]
    # per-cell nan count
    nn = np.sum(~np.isnan(v), axis=0)  # (60,60)
    # hazen: h = (n_per_cell)*p + 0.5 ... but n varies per cell! use vectorized per-cell
    # For cells with all-valid n: h = n*0.9+0.5; index floor(h)-1, frac h-floor(h)
    with np.errstate(invalid="ignore"):
        h = nn * 0.9 + 0.5
    h = np.where(nn > 0, h, np.nan)
    lo_i = np.floor(h).astype(int) - 1  # 0-based
    frac = h - np.floor(h)
    # clamp indices
    lo_i_c = np.clip(lo_i, 0, n-1)
    hi_i_c = np.clip(lo_i+1, 0, n-1)
    v_lo = np.take_along_axis(s, lo_i_c[None], axis=0)[0]
    v_hi = np.take_along_axis(s, hi_i_c[None], axis=0)[0]
    q = v_lo + frac * (v_hi - v_lo)
    q = np.where(nn > 0, q, np.nan)
    thr[dd-1] = q
print("quantile+mean time:", round(time.time()-t0,1), "s")
np.save("/work/thr_raw.npy", thr); np.save("/work/clim_raw.npy", clim)
print("thr raw sample d=167 cell(0,0):", thr[166,0,0], "clim:", clim[166,0,0])
print("thr d60 before fill:", thr[59,0,0], "clim:", clim[59,0,0])
