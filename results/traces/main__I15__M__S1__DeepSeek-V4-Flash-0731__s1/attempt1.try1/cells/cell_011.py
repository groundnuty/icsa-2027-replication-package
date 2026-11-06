import numpy as np
from datetime import datetime, timedelta
import xarray as xr

# Load target data and determine sea cells
target_start = datetime(2019, 6, 1)
target_end = datetime(2019, 8, 31)

# Get lat/lon indices for region
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_mask = (lats >= 56.13) & (lats <= 57.33)
lon_mask = (lons >= 17.71) & (lons <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

# Target dates
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)
n_target = len(target_dates)

# Load target SST
target_sst = np.zeros((n_target, len(lat_idx), len(lon_idx)), dtype=np.float64)
for i, date in enumerate(target_dates):
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    sst = ds['analysed_sst'].values[0]
    target_sst[i] = sst[np.ix_(lat_idx, lon_idx)].astype(np.float64)
    ds.close()

# Sea mask: finite on all target days
sea_mask = np.all(~np.isnan(target_sst), axis=0)
n_sea = sea_mask.sum()
print(f"Sea cells: {n_sea}")

# Save for later
np.save('/tmp/target_sst.npy', target_sst)
np.save('/tmp/sea_mask.npy', sea_mask)
np.save('/tmp/lat_idx.npy', lat_idx)
np.save('/tmp/lon_idx.npy', lon_idx)
print("Saved target data and masks")
