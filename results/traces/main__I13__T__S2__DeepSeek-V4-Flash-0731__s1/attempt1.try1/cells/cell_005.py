
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    # Select the region
    region = ds.sel(latitude=slice(56.09, 57.29), longitude=slice(10.55, 11.75))
    print("Region shape:", region.analysed_sst.shape)
    print(region.latitude.values)
    print(region.longitude.values)
