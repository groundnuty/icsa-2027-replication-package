
import xarray as xr, fsspec, numpy as np

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Select region
lat_mask = (ds.latitude >= 64.39) & (ds.latitude <= 65.59)
lon_mask = (ds.longitude >= 23.41) & (ds.longitude <= 24.61)
print("Lat mask sum:", lat_mask.sum().item(), "Lon mask sum:", lon_mask.sum().item())

# Select the region data
ds_reg = ds.isel(latitude=lat_mask, longitude=lon_mask)
print(ds_reg)
