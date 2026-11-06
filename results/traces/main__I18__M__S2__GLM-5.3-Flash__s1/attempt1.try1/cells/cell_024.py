import os, json, warnings, time as tm
import numpy as np
import h5py
import xarray as xr

print("cwd:", os.getcwd())
os.makedirs("output", exist_ok=True)

PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
EPOCH = np.datetime64("1970-01-01")

with h5py.File(PATH, "r") as f:
    times = EPOCH + f["time"][:].astype("timedelta64[s]")   # WRONG epoch intentionally avoided
with xr.open_dataset(PATH, engine="h5netcdf") as dst:
    times = dst["time"].values.astype("datetime64[D]")       # correctly decoded
    lat = dst["latitude"].values.astype(np.float32)
    lon = dst["longitude"].values.astype(np.float32)
assert times[0] == np.datetime64("1982-01-01") and times[-1] == np.datetime64("2023-12-31")

lat = lat.astype(np.float64); lon = lon.astype(np.float64)
ii = int(np.searchsorted(lat, 57.13, side="left")); jj = int(np.searchsorted(lat, 58.33, side="right"))
kk = int(np.searchsorted(lon, 22.79, side="left")); ll = int(np.searchsorted(lon, 23.99, side="right"))
assert (ii, jj, kk, ll) == (182, 242, 690, 750)
print("region slice:", lat[ii], "..", lat[jj-1], "|", lon[kk], "..", lon[ll-1])

i0b = int(np.searchsorted(times, np.datetime64("1991-12-27")))
i1b = int(np.searchsorted(times, np.datetime64("2003-01-05"), side="right"))
i0t = int(np.searchsorted(times, np.datetime64("2010-06-01")))
i1t = int(np.searchsorted(times, np.datetime64("2010-08-31"), side="right"))
assert (i0b, i1b, i0t, i1t) == (3647, 7675, 10378, 10470)

with h5py.File(PATH, "r") as f:
    base = f["analysed_sst"][i0b:i1b, ii:jj, kk:ll].astype(np.float64)
    tgt  = f["analysed_sst"][i0t:i1t, ii:jj, kk:ll].astype(np.float64)
print("base", base.shape, "tgt", tgt.shape)
assert np.array_equal(base, np.load("/tmp/base.npy"), equal_nan=True)
assert np.array_equal(tgt, np.load("/tmp/tgt.npy"), equal_nan=True)
print("re-extraction matches intermediates exactly")

bdates = times[i0b:i1b]
tdates = times[i0t:i1t]
print("bdates:", bdates[0], bdates[-1], " tdates:", tdates[0], tdates[-1])
assert np.array_equal(bdates, np.arange(bdates[0], bdates[-1]+1).astype("datetime64[D]"))
assert np.array_equal(tdates, np.arange(tdates[0], tdates[-1]+1).astype("datetime64[D]"))

def doy366(dates):
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    doy_std = (dates - (years - 1970).astype("datetime64[Y]")).astype(int) + 1
    leap = (years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))
    return np.where(leap | (doy_std < 60), doy_std, doy_std + 1)

doy_b = doy366(bdates)
doy_t = doy366(tdates)
assert doy_t[0] == 153 and doy_t[-1] == 244

baseline_mask = (bdates >= np.datetime64("1992-01-01")) & (bdates <= np.datetime64("2002-12-31"))
assert baseline_mask.sum() == 4018
base_daynum = (bdates - EPOCH).astype(int)
bstart = base_daynum[0]

thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
pool_sizes = []
t0 = tm.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        members = bdates[baseline_mask & (doy_b == d)]
        assert len(members) == 11
        pool_days = set()
        for m in members:
            mnum = int((m - EPOCH) / np.timedelta64(1, "D"))
            pool_days.update(range(mnum - 5, mnum + 6))
        sel = np.array(sorted(pool_days)) - bstart
        assert sel.min() >= 0 and sel.max() < len(bdates)
        pool = base[sel]
        pool_sizes.append(len(sel))
        thr_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
        clim_raw[d-1] = np.nanmean(pool, axis=0)
print("pool loop:", round(tm.time()-t0, 1), "s | pool sizes min/max:", min(pool_sizes), max(pool_sizes))
thr_raw[59] = 0.5 * (thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5 * (clim_raw[58] + clim_raw[60])
print("thr_raw matches intermediate:", np.allclose(thr_raw, np.load("/tmp/thr_raw.npy"), equal_nan=True))
print("clim_raw matches intermediate:", np.allclose(clim_raw, np.load("/tmp/clim_raw.npy"), equal_nan=True))

def circ_moving_mean(arr, window=31):
    half = window // 2
    idx = np.array([(np.arange(366) - off) % 366 for off in range(-half, half + 1)])
    acc = np.zeros_like(arr)
    for k in range(window):
        acc += arr[idx[k]]
    return acc / window

thr = circ_moving_mean(thr_raw)
clim = circ_moving_mean(clim_raw)
print("thr matches intermediate:", np.allclose(thr, np.load("/tmp/thr.npy"), equal_nan=True))
print("clim matches intermediate:", np.allclose(clim, np.load("/tmp/clim.npy"), equal_nan=True))
# manual spot checks (verified index arithmetic)
assert abs(thr[149, 30, 30] - thr_raw[134:165, 30, 30].mean()) < 1e-9
assert abs(thr[0, 30, 30] - np.concatenate([thr_raw[351:366, 30, 30], thr_raw[0:16, 30, 30]]).mean()) < 1e-9
assert abs(clim[199, 30, 30] - clim_raw[184:215, 30, 30].mean()) < 1e-9
assert abs(clim[0, 30, 30] - np.concatenate([clim_raw[351:366, 30, 30], clim_raw[0:16, 30, 30]]).mean()) < 1e-9
print("manual smoothing spot checks passed")

sea = np.isfinite(tgt).all(axis=0)
print("sea cells:", int(sea.sum()), "land cells:", int((~sea).sum()))
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    hot = tgt >= thr[doy_t - 1]
assert np.array_equal(hot, np.load("/tmp/hot_finalcheck.npy") if os.path.exists("/tmp/hot_finalcheck.npy") else np.load("/tmp/hot.npy"), )
print("hot mask matches intermediate")
