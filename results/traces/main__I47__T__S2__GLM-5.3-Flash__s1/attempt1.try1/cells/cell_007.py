import numpy as np, datetime as dt, json, os, time, warnings
from numpy.lib.stride_tricks import sliding_window_view
import fsspec, h5py

warnings.simplefilter("error", RuntimeWarning)  # surface any numeric surprise
t_start = time.time()
np.set_printoptions(precision=4, suppress=True)

# ================= configuration =================
PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
LAT_MIN, LAT_MAX = np.float32(64.39), np.float32(65.59)
LON_MIN, LON_MAX = np.float32(23.41), np.float32(24.61)
T0, T1 = '2019-06-01', '2019-08-31'
B0, B1 = '1992-01-01', '2002-12-31'
E0, E1 = '1991-12-27', '2003-01-05'          # extended pool window
Q = 0.9
W = 5                                        # +/- calendar-day window
HALF = 15                                    # 31-day centred moving mean

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # leap-aligned
def mdoy(dates):                              # dates: datetime64[D] array
    months = dates.astype('datetime64[M]').astype(int) % 12 + 1
    days = (dates - dates.astype('datetime64[M]')).astype('timedelta64[D]').astype(int) + 1
    return CUM[months-1] + days

# ================= read data =================
fs = fsspec.filesystem('onedata')
f = fs.open(PATH, 'rb')
hf = h5py.File(f, 'r')
dset = hf['analysed_sst']
lat = hf['latitude'][:]; lon = hf['longitude'][:]
tvals = hf['time'][:]
epoch = np.datetime64('1981-01-01')
dates = epoch + tvals.astype('timedelta64[s]')
dates = dates.astype('datetime64[D]')
hf.close(); f.close()
assert np.array_equal(np.diff(dates).astype(int), np.ones(len(dates)-1)), "time not contiguous daily"

ii = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
jj = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
i0, i1, j0, j1 = ii[0], ii[-1]+1, jj[0], jj[-1]+1
print(f"region: lat idx {ii[0]}..{ii[-1]} ({ii[-1]-ii[0]+1}), lon idx {jj[0]}..{jj[-1]} ({jj[-1]-jj[0]+1})")
print(f"lat {lat[ii[0]]}..{lat[ii[-1]]}, lon {lon[jj[0]]}..{lon[jj[-1]]}")

def idx_of(datestr): return int((np.datetime64(datestr) - dates[0]) / np.timedelta64(1, 'D'))

# target period
tA, tB = idx_of(T0), idx_of(T1)
arrT = dset[tA:tB+1, i0:i1, j0:j1].astype(np.float64)     # (92,60,60)
target_dates = dates[tA:tB+1]
nT = len(target_dates)
print(f"target: {target_dates[0]}..{target_dates[-1]} ({nT} days)")

# sea cells: finite on every target day
sea2d = np.isfinite(arrT).all(axis=0)
sea = sea2d.ravel()
nsea = int(sea.sum())
print(f"sea cells: {nsea} / {sea.size}  (land/ice-masked: {sea.size - nsea})")

# extended baseline read
eA, eB = idx_of(E0), idx_of(E1)
arr44 = dset[eA:eB+1, i0:i1, j0:j1].astype(np.float64)    # (4028,60,60)
ext_dates = dates[eA:eB+1]
bA, bB = idx_of(B0), idx_of(B1)
print(f"extended window: {ext_dates[0]}..{ext_dates[-1]} ({len(ext_dates)} days); "
      f"baseline {dates[bA]}..{dates[bB]} ({bB-bA+1} days)")
print(f"reads done at {time.time()-t_start:.1f}s")

# ================= pools -> raw threshold & climatology =================
doy_ext = mdoy(ext_dates)
nlon = len(jj)
thr_raw = np.full((366, nsea), np.nan)
clim_raw = np.full((366, nsea), np.nan)
pool_counts = np.zeros(366, int)
nanpool = np.zeros(366, int)

arr44_sea = arr44.reshape(len(ext_dates), -1)[:, sea]      # (4028, nsea) float64
del arr44

for d in range(1, 367):
    if d == 60:
        continue                                            # no pool of its own
    w = np.abs(doy_ext - d) <= W                            # +/-5 calendar days
    idx = np.nonzero(w)[0]
    pool = arr44_sea[idx]                                   # (nd, nsea) copy
    pool_counts[d-1] = len(idx)
    s = np.sort(pool, axis=0)
    n = np.count_nonzero(np.isfinite(pool), axis=0)
    nanpool[d-1] = int((n == 0).sum())
    v = Q*n - 0.5                                           # Hazen / MATLAB default
    lo = np.clip(np.floor(v).astype(np.int64), 0, np.maximum(n-1, 0))
    hi = np.minimum(lo+1, np.maximum(n-1, 0))
    site_g = v - np.floor(v)
    cols = np.arange(nsea)
    q = s[lo, cols] + site_g*(s[hi, cols] - s[lo, cols])
    q[n == 0] = np.nan
    thr_raw[d-1] = q
    clim_raw[d-1] = np.nanmean(pool, axis=0)

# day 60 := mean of days 59 and 61 (pre-smoothing)
for A in (thr_raw, clim_raw):
    A[59] = 0.5*(A[58] + A[60])
print(f"pools built at {time.time()-t_start:.1f}s")
print("pool size stats: min", pool_counts[pool_counts>0].min(), "max", pool_counts.max(),
      "| doy 60 pool size:", pool_counts[59])
print("pools all-NaN (per doy) counts:", np.unique(nanpool, return_counts=True))

# in-situ validation of hazen on one real pool
idx = np.nonzero(np.abs(doy_ext - 200) <= W)[0]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ref = np.nanquantile(arr44_sea[idx], Q, axis=0, method='hazen')
print("in-situ hazen vs numpy max|diff|:", np.nanmax(np.abs(thr_raw[199] - ref)))

# ================= circular 31-day smoothing =================
def circ31(x):                                              # x: (366, k)
    xp = np.concatenate([x[-HALF:], x, x[:HALF]], axis=0)
    return sliding_window_view(xp, 2*HALF+1, axis=0).mean(axis=-1)

thr = circ31(thr_raw)
clim = circ31(clim_raw)
print(f"smoothing done at {time.time()-t_start:.1f}s")
print("NaN in smoothed thr/clim over sea cells:", int(np.isnan(thr).sum()), int(np.isnan(clim).sum()))

# ================= hot days & per-cell MHWs =================
doy_t = mdoy(target_dates)                                  # leap-aligned doys of target
sst = arrT.reshape(nT, -1)[:, sea]                          # (92, nsea)
hot = sst >= thr[doy_t - 1]                                 # NaN SST -> False
print(f"hot days total over sea cells: {int(hot.sum())} of {hot.size}")

# runs >= 5, then join gaps <= 2  (vectorized interval logic, verified earlier)
def cell_mhw(hotmat):
    T, N = hotmat.shape
    z = np.zeros((T+2, N), np.int8); z[1:-1] = hotmat
    dz = z[1:] - z[:-1]
    out = np.zeros((T, N), bool)
    total = 0
    for c in range(N):
        col = dz[:, c]
        ss = np.nonzero(col == 1)[0]; ee = np.nonzero(col == -1)[0]
        ivals = [[a, b-1] for a, b in zip(ss, ee)]
        ivals = [iv for iv in ivals if iv[1]-iv[0]+1 >= 5]
        merged = []
        for a, b in ivals:
            if merged and a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
            else: merged.append([a, b])
        for a, b in merged:
            out[a:b+1, c] = True; total += 1
    return out, total

mhw_sea, n_cell_mhw = cell_mhw(hot)
print(f"per-cell MHWs (after joining): {n_cell_mhw}")
print(f"per-cell MHW cell-days: {int(mhw_sea.sum())}")

# ================= regional events =================
active = mhw_sea.any(axis=1)                                # any sea cell in MHW
mhw_full = np.zeros((nT, sea.size), np.uint8)
mhw_full[:, sea] = mhw_sea.astype(np.uint8)
mhw_full = mhw_full.reshape(nT, len(ii), len(jj))
print(f"active days: {int(active.sum())} / {nT}")

events = []
i = 0
while i < nT:
    if active[i]:
        j = i
        while j+1 < nT and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else:
        i += 1
print("regional events:", len(events))
for a, b in events:
    print(f"  {target_dates[a]} .. {target_dates[b]}  ({b-a+1} days)")

# ================= diagnostics =================
print("\nclim/threshold sanity (sea cells, target doys):")
for k in (0, nT//2, nT-1):
    d0 = doy_t[k]-1
    print(f"  {target_dates[k]} doy {doy_t[k]}: clim mean {np.nanmean(clim[d0]):.3f} K, "
          f"thr mean {np.nanmean(thr[d0]):.3f} K, SST mean {np.nanmean(sst[k]):.3f} K, "
          f"hot cells {int(hot[k].sum())}, MHW cells {int(mhw_sea[k].sum())}")
np.save('/tmp/mhw.npy', mhw_full)
np.save('/tmp/meta.npy', np.array([i0, i1, j0, j1, nT, nsea], dtype=np.int64))
with open('/tmp/events.json', 'w') as fh:
    json.dump({"events": [[str(target_dates[a]), str(target_dates[b])] for a, b in events]}, fh)
print(f"\nTOTAL {time.time()-t_start:.1f}s")
