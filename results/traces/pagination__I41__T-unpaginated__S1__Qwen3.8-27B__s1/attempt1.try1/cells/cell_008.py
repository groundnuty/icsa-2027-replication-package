
import numpy as np, json
from datetime import date, timedelta

d = np.load('/tmp/sst_data.npz')
master = d['master']          # (4028, 60, 60) 1991-12-27..2003-01-05
target = d['target']          # (92, 60, 60) 2021-06-01..2021-08-31
lat_r  = d['lat_region']      # (60,)
lon_r  = d['lon_region']      # (60,)

def daterange(a, b):
    out = []
    while a <= b:
        out.append(a); a += timedelta(days=1)
    return out
base_dates = daterange(date(1991,12,27), date(2003,1,5))
tgt_dates  = daterange(date(2021,6,1), date(2021,8,31))

# --- day-of-year mapping (leap-year calendar, 1..366, 29 Feb = 60) ---
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
cum = [0]
for m in mdays: cum.append(cum[-1]+m)
def doy(m, dd): return cum[m-1] + dd
assert doy(1,1)==1 and doy(2,28)==59 and doy(2,29)==60 and doy(3,1)==61 and doy(12,31)==366

# --- sea cells: finite on every target day ---
sea = np.isfinite(target).all(axis=0)          # (60,60)
sea_cells = np.argwhere(sea)
n_sea = len(sea_cells)
print("sea cells:", n_sea, "of 3600")

M = master[:, sea[0], :][:, :, :]  # placeholder, wrong shape; do properly below
M = np.empty((4028, n_sea), np.float64)
for j, (i, k) in enumerate(sea_cells):
    M[:, j] = master[:, i, k]
T = np.empty((92, n_sea), np.float64)
for j, (i, k) in enumerate(sea_cells):
    T[:, j] = target[:, i, k]

# --- pools per day of year ---
base_all = daterange(date(1992,1,1), date(2002,12,31))
mord = np.array([x.toordinal() for x in base_dates], dtype=np.int64)
bords = np.array([x.toordinal() for x in base_all], dtype=np.int64)
bdoy  = np.array([doy(x.month, x.day) for x in base_all], dtype=np.int32)
tdoy  = np.array([doy(x.month, x.day) for x in tgt_dates], dtype=np.int32)

pool_idx = {}
pool_sizes = {}
for dd in range(1, 367):
    if dd == 60:
        continue
    b = bords[bdoy == dd]
    mask = np.zeros(4028, dtype=bool)
    for bo in b:
        mask |= (mord >= bo-5) & (mord <= bo+5)
    idx = np.where(mask)[0]
    pool_idx[dd] = idx
    pool_sizes[dd] = len(idx)
import collections
print("pool size histogram:", collections.Counter(pool_sizes.values()))
print("doy 1 dates:", base_dates[pool_idx[1][0]], "..", base_dates[pool_idx[1][-1]])
print("doy 365 dates:", base_dates[pool_idx[365][0]], "..", base_dates[pool_idx[365][-1]])

# --- threshold & climatology (float64, hazen 90th pct / mean, NaN ignored) ---
thr = np.full((367, n_sea), np.nan)
clim = np.full((367, n_sea), np.nan)
import warnings
for dd in range(1, 367):
    if dd == 60: continue
    blk = M[pool_idx[dd], :]            # (121, n_sea)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        thr[dd, :] = np.nanquantile(blk, 0.9, axis=0, method="hazen")
        clim[dd, :] = np.nanmean(blk, axis=0)
# day 60 = mean of 59 and 61
thr[60, :] = 0.5*(thr[59, :] + thr[61, :])
clim[60, :] = 0.5*(clim[59, :] + clim[61, :])
print("thr any NaN after fill:", bool(np.isnan(thr).any()), " clim any NaN:", bool(np.isnan(clim).any()))

# --- wrap-around 31-day centred moving mean over 366 elements ---
def smooth366(a):   # a: (366, n)
    s = np.zeros_like(a)
    for k in range(31):
        s += np.roll(a, -k, axis=0)
    s += np.roll(a, 15, axis=0)
    return s / 31.0
thrs = smooth366(thr[:366])
clims = smooth366(clim[:366])
print("thr summer (152..242) range: %.2f .. %.2f K" % (np.nanmin(thrs[152:243, :]), np.nanmax(thrs[152:243, :])))
print("clim summer range: %.2f .. %.2f K" % (np.nanmin(clims[152:243, :]), np.nanmax(clims[152:243, :])))
print("SST summer range: %.2f .. %.2f K" % (np.nanmin(T[:, :]), np.nanmax(T[:, :])))

np.savez_compressed('/tmp/mhw_stage2.npz',
                    T=T, sea_cells=sea_cells, thrs=thrs, clim=clims,
                    tgt_doy=tdoy, lat_r=lat_r, lon_r=lon_r,
                    tgt0=tgt_dates[0].toordinal(), n_sea=np.int64(n_sea))
print("stage2 saved")
