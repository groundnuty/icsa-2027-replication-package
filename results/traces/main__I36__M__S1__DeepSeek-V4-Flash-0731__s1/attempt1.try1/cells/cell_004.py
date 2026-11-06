
import xarray as xr
import os
import numpy as np

# Open a file to check coordinates
f = os.path.join('/data/icsa2027_data_20261101T090944Z/s1z', 'sst_20030601.nc')
ds = xr.open_dataset(f, engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
print(f"lat range: {lat.min()} to {lat.max()}, step: {lat[1]-lat[0]}")
print(f"lon range: {lon.min()} to {lon.max()}, step: {lon[1]-lon[0]}")

# Find region indices
lat_mask = (lat >= 60.09) & (lat <= 61.29)
lon_mask = (lon >= 20.01) & (lon <= 21.21)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"lat_idx: {lat_idx.min()} to {lat_idx.max()}, count: {len(lat_idx)}")
print(f"lon_idx: {lon_idx.min()} to {lon_idx.max()}, count: {len(lon_idx)}")
print(f"Lat values in region: {lat[lat_idx]}")
print(f"Lon values in region: {lon[lon_idx]}")

# Check the SST values for this file
sst = ds.analysed_sst.values[0, lat_idx.min():lat_idx.max()+1, lon_idx.min():lon_idx.max()+1]
print(f"SST shape: {sst.shape}")
print(f"SST range: {np.nanmin(sst)} to {np.nanmax(sst)}")
print(f"NaN count: {np.isnan(sst).sum()}")
print(f"Non-NaN count: {np.sum(~np.isnan(sst))}")
ds.close()
