import numpy as np, pandas as pd, time as timer, fsspec, xarray as xr
print("numpy", np.__version__, "xarray", xr.__version__, "pandas", pd.__version__)
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values
latidx = np.where((lat >= 56.13) & (lat <= 57.33))[0]
lonidx = np.where((lon >= 17.71) & (lon <= 18.91))[0]
times = pd.DatetimeIndex(ds.time.values)
t0 = timer.time()
v = ds.analysed_sst.isel(time=slice(3660, 3760), latitude=latidx, longitude=lonidx).values.astype(np.float64)
dt = timer.time()-t0
print("100-day read:", round(dt,2), "s -> est for 4120 days:", round(dt/100*4120/60,1), "min")
print("stats: min", np.nanmin(v), "max", np.nanmax(v), "finite frac", np.isfinite(v).mean())
