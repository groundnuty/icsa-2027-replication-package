import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    lat = ds.latitude
    lon = ds.longitude
    lat_mask = (lat >= 57.57) & (lat <= 58.77)
    lon_mask = (lon >= 10.25) & (lon <= 11.45)
    print(f"Lat size: {len(lat)}, Masked lat size: {lat_mask.sum().values}")
    print(f"Lon size: {len(lon)}, Masked lon size: {lon_mask.sum().values}")
