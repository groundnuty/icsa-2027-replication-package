import h5py, time, numpy as np, xarray as xr, pandas as pd, os
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
os.makedirs("work", exist_ok=True)
ds = xr.open_dataset(path, engine="h5netcdf")
times = pd.DatetimeIndex(ds.time.values)
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
ds.close()

assert len(times) == 15340
assert times[0] == pd.Timestamp("1982-01-01")
assert times[-1] == pd.Timestamp("2023-12-31")
assert (np.diff(times.asi8) == 86400*10**9).all(), "time not strictly daily"
tindex = {t.normalize(): i for i, t in enumerate(times)}

i0, i1 = 322, 381
j0, j1 = 485, 544
latv = lat[i0:i1+1]; lonv = lon[j0:j1+1]
assert latv.min() >= 59.93 and latv.max() <= 61.13 and lonv.min() >= 18.69 and lonv.max() <= 19.89

baseline_dates = pd.date_range("1991-12-27", "2003-01-05", freq="D")
target_dates   = pd.date_range("2007-06-01", "2007-08-31", freq="D")
for block in (baseline_dates, target_dates):
    ks = [tindex[d] for d in block]
    assert (np.diff(ks) == 1).all(), "block not contiguous: " + str(block[0])
k_base = np.array([tindex[d] for d in baseline_dates])
k_targ = np.array([tindex[d] for d in target_dates])
print("baseline block:", baseline_dates[0].date(), "->", baseline_dates[-1].date(), "idx", k_base[0], "->", k_base[-1])
print("target block  :", target_dates[0].date(), "->", target_dates[-1].date(), "idx", k_targ[0], "->", k_targ[-1])
print("gap between blocks (expected, not read):", target_dates[0] - baseline_dates[-1])

f = h5py.File(path, "r"); d = f["analysed_sst"]
nb, nt = len(baseline_dates), len(target_dates)
base = np.empty((nb, 60, 60), dtype=np.float64)
targ = np.empty((nt, 60, 60), dtype=np.float64)
t0 = time.time()
for n, k in enumerate(k_base):
    base[n] = d[k, i0:i1+1, j0:j1+1]
for n, k in enumerate(k_targ):
    targ[n] = d[k, i0:i1+1, j0:j1+1]
t1 = time.time()
print("read", nb+nt, "planes in", round(t1-t0,1), "s")
f.close()
np.savez_compressed("work/data.npz",
    base=base, targ=targ,
    base_dates=baseline_dates.strftime("%Y-%m-%d").values.astype("S10"),
    targ_dates=target_dates.strftime("%Y-%m-%d").values.astype("S10"),
    lat=latv, lon=lonv)
print("saved. base", base.shape, "targ", targ.shape)
print("base finite frac", round(np.isfinite(base).mean(),4), "| targ finite frac", round(np.isfinite(targ).mean(),4))
# distribution of per-day finite counts (informal land/sea look)
fin_per_day_base = np.isfinite(base).reshape(nb, -1).sum(1)
fin_per_day_targ = np.isfinite(targ).reshape(nt, -1).sum(1)
print("base per-day finite cells: min", fin_per_day_base.min(), "max", fin_per_day_base.max())
print("targ per-day finite cells: min", fin_per_day_targ.min(), "max", fin_per_day_targ.max())
print("SST range base:", np.nanmin(base), np.nanmax(base), "| targ:", np.nanmin(targ), np.nanmax(targ))
