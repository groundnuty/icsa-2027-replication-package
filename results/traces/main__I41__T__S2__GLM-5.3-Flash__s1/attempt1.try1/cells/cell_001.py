import sys
print(sys.version)
import numpy as np, pandas as pd, xarray as xr, fsspec
print("numpy", np.__version__, "| pandas", pd.__version__, "| xarray", xr.__version__)
try:
    import h5netcdf; print("h5netcdf", h5netcdf.__version__)
except Exception as e:
    print("h5netcdf missing:", e)

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("dims:", dict(ds.sizes))
    print("vars:", list(ds.variables))
    print("data_vars:", list(ds.data_vars))
    for v in ds.data_vars:
        print(v, ds[v].dtype, ds[v].dims, {k: ds[v].attrs[k] for k in list(ds[v].attrs)})
    t = ds['time'].values
    print("time dtype:", t.dtype, "n =", len(t))
    print("time first:", t[0], " last:", t[-1])
    lat = ds['lat'].values; lon = ds['lon'].values
    print("lat: min", lat.min(), "max", lat.max(), "n", len(lat), "first steps", np.round(np.diff(lat)[:3], 6))
    print("lon: min", lon.min(), "max", lon.max(), "n", len(lon), "first steps", np.round(np.diff(lon)[:3], 6))
    print("coords attrs lat:", dict(ds['lat'].attrs), "lon:", dict(ds['lon'].attrs), "time:", dict(ds['time'].attrs))
    print("global attrs keys:", list(ds.attrs.keys()))
