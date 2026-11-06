
import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')

# Open a file to check the data
f = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds.analysed_sst.values.shape)
print(ds.time.values)
print(ds.latitude.values.min(), ds.latitude.values.max())
print(ds.longitude.values.min(), ds.longitude.values.max())

# Check region
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

# Find indices for the region
lat_idx = (ds.latitude.values >= lat_min) & (ds.latitude.values <= lat_max)
lon_idx = (ds.longitude.values >= lon_min) & (ds.longitude.values <= lon_max)
print("Lat indices count:", lat_idx.sum())
print("Lon indices count:", lon_idx.sum())
print("Lat values:", ds.latitude.values[lat_idx])
print("Lon values:", ds.longitude.values[lon_idx])

# Extract region data
region_sst = ds.analysed_sst.values[0, lat_idx, :][:, lon_idx]
print("Region SST shape:", region_sst.shape)
print("Non-NaN:", ~np.isnan(region_sst))
import numpy as np
print("Non-NaN count:", (~np.isnan(region_sst)).sum())
