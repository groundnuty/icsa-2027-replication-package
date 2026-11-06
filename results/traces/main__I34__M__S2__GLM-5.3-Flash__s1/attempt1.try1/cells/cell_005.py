import h5py, time, numpy as np, xarray as xr, pandas as pd, os
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
os.makedirs("work", exist_ok=True)
ds = xr.open_dataset(path, engine="h5netcdf")
times = pd.DatetimeIndex(ds.time.values)
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
ds.close()

# --- sanity checks on the time axis ---
assert len(times) == 15340
assert times[0] == pd.Timestamp("1982-01-01")
assert times[-1] == pd.Timestamp("2023-12-31")
assert (np.diff(times.asi8) == 86400*10**9).all(), "time not strictly daily"
assert len(set(times)) == len(times), "duplicate dates"
tindex = {t.normalize(): i for i, t in enumerate(times)}

# --- region box ---
latmask = (lat >= 59.93) & (lat <= 61.13)
lonmask = (lon >= 18.69) & (lon <= 19.89)
i0, i1 = np.where(latmask)[0][[0,-1]]
j0, j1 = np.where(lonmask)[0][[0,-1]]
assert np.all(latmask[i0:i1+1]) and np.all(lonmask[j0:j1+1])
print("box: lat", lat[i0], "->", lat[i1], "idx", i0, i1, "| lon", lon[j0], "->", lon[j1], "idx", j0, j1)

# --- date sets ---
baseline_dates = pd.date_range("1991-12-27", "2003-01-05", freq="D")  # pool dates incl. window overhang
target_dates   = pd.date_range("2007-06-01", "2007-08-31", freq="D")
all_dates = baseline_dates.append(target_dates)
missing = [d for d in all_dates if d not in tindex]
print("dates requested:", len(all_dates), "missing:", missing)
assert not missing
k_all = np.array([tindex[d] for d in all_dates])
assert (np.diff(k_all) == 1).all(), "selected dates not contiguous"
print("baseline idx range:", tindex[baseline_dates[0]], tindex[baseline_dates[-1]], "| target idx range:", tindex[target_dates[0]], tindex[target_dates[-1]])
print("baseline within baseline-period check: first", baseline_dates[0], "last", baseline_dates[-1])

# --- stream read ---
f = h5py.File(path, "r"); d = f["analysed_sst"]
nb = len(baseline_dates); nt = len(target_dates); nlat, nlon = i1-i0+1, j1-j0+1
base = np.empty((nb, nlat, nlon), dtype=np.float64)
targ = np.empty((nt, nlat, nlon), dtype=np.float64)
t0 = time.time()
for n, k in enumerate(k_all):
    box = d[k, i0:i1+1, j0:j1+1]
    if n < nb: base[n] = box
    else:      targ[n-nb] = box
t1 = time.time()
print("read", len(k_all), "planes in", round(t1-t0,1), "s")
f.close()
np.savez_compressed("work/data.npz",
    base=base, targ=targ,
    base_dates=baseline_dates.strftime("%Y-%m-%d").values.astype("S10"),
    targ_dates=target_dates.strftime("%Y-%m-%d").values.astype("S10"),
    lat=lat[i0:i1+1], lon=lon[j0:j1+1])
print("saved. base", base.shape, base.dtype, "targ", targ.shape, targ.dtype)
print("base finite frac", np.isfinite(base).mean(), "| targ finite frac", np.isfinite(targ).mean())
