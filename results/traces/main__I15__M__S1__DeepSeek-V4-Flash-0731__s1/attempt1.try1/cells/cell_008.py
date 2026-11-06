import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Determine target period dates
target_start = datetime(2019, 6, 1)
target_end = datetime(2019, 8, 31)

# Load target data for region
lat_idx_all = None
lon_idx_all = None

# Get lat/lon indices
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_mask = (lats >= 56.13) & (lats <= 57.33)
lon_mask = (lons >= 17.71) & (lons <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

# Load all target days
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

print(f"Target days: {len(target_dates)}")

# Collect target SST data
target_sst = np.zeros((len(target_dates), len(lat_idx), len(lon_idx)), dtype=np.float64)
for i, date in enumerate(target_dates):
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    sst = ds['analysed_sst'].values[0]
    target_sst[i] = sst[np.ix_(lat_idx, lon_idx)].astype(np.float64)
    ds.close()

print(f"Target SST shape: {target_sst.shape}")

# Determine sea cells (finite on all target days)
sea_mask = np.all(~np.isnan(target_sst), axis=0)
print(f"Sea cells: {sea_mask.sum()}, Land cells: {np.sum(~sea_mask)}")
print(f"Sea mask shape: {sea_mask.shape}")
