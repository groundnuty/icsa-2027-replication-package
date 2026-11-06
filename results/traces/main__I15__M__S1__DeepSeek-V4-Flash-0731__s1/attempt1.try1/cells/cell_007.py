import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Get the grid for the region
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_mask = (lats >= 56.13) & (lats <= 57.33)
lon_mask = (lons >= 17.71) & (lons <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"Region: {len(lat_idx)} lat cells x {len(lon_idx)} lon cells = {len(lat_idx)*len(lon_idx)} cells")

# Check the target period data for these cells
sst = ds['analysed_sst'].values[0]
region_sst = sst[np.ix_(lat_idx, lon_idx)]
print(f"Region SST shape: {region_sst.shape}")
print(f"NaN in region: {np.isnan(region_sst).sum()}")
print(f"Total cells: {region_sst.size}")
print(f"Non-NaN: {np.sum(~np.isnan(region_sst))}")
