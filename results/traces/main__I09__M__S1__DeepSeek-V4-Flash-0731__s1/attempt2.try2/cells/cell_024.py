
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

# Load data
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
lat_idx = np.load('/tmp/lat_idx.npy')
lon_idx = np.load('/tmp/lon_idx.npy')

# Load coordinates from the dataset
data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
f0 = os.path.join(data_dir, 'sst_20220601.nc')
ds0 = xr.open_dataset(f0, engine='h5netcdf')
lats = ds0.latitude.values[lat_idx]
lons = ds0.longitude.values[lon_idx]
ds0.close()

# Target dates
target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

print(f"Lat coords: {lats[0]} to {lats[-1]}, count={len(lats)}")
print(f"Lon coords: {lons[0]} to {lons[-1]}, count={len(lons)}")
print(f"Time: {target_dates[0]} to {target_dates[-1]}, count={len(target_dates)}")
print(f"MHW mask shape: {mhw_mask.shape}")

# Create NetCDF
times = np.array(target_dates, dtype='datetime64[ns]')

# Create output directory
os.makedirs('output', exist_ok=True)

# Create the dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask.astype(np.uint8)),
    },
    coords={
        'time': times,
        'lat': lats,
        'lon': lons,
    }
)

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("NetCDF written successfully")

# Verify
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"Verified: shape={ds_check.mhw.shape}, dtype={ds_check.mhw.dtype}")
print(f"Time: {ds_check.time.values[0]} to {ds_check.time.values[-1]}")
print(f"Lat: {ds_check.lat.values[0]} to {ds_check.lat.values[-1]}")
print(f"Lon: {ds_check.lon.values[0]} to {ds_check.lon.values[-1]}")
print(f"MHW values: {np.unique(ds_check.mhw.values)}")
ds_check.close()
