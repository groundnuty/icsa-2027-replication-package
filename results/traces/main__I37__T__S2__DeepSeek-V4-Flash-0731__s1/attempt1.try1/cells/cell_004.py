
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dims:", dict(ds.sizes))
    print("Time range:", ds.time.values[0], ds.time.values[-1], len(ds.time))
    print("Lat range:", float(ds.latitude.values.min()), float(ds.latitude.values.max()), len(ds.latitude))
    print("Lon range:", float(ds.longitude.values.min()), float(ds.longitude.values.max()), len(ds.longitude))
    print("Lat values (first 10):", ds.latitude.values[:10])
    print("Lon values (first 10):", ds.longitude.values[:10])
    print("Time first 5:", ds.time.values[:5])
    print("Data var:", list(ds.data_vars))
    # Check a few values
    print("SST shape:", ds.analysed_sst.shape)
    print("SST dtype:", ds.analysed_sst.dtype)
