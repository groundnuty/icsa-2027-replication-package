
import os
import numpy as np
from datetime import date
import xarray as xr
import h5py

# Load data
cell_mhw = np.load('/tmp/cell_mhw.npy')
with open('/tmp/target_dates.txt') as f:
    target_dates_str = [line.strip() for line in f]
target_dates = [date.fromisoformat(s) for s in target_dates_str]

# Load region coordinates from dataset
base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
with h5py.File(os.path.join(base_dir, 'sst_20030601.nc'), 'r') as h5:
    lat = h5['latitude'][:]
    lon = h5['longitude'][:]
lat_idx = np.where((lat >= 60.09) & (lat <= 61.29))[0]
lon_idx = np.where((lon >= 20.01) & (lon <= 21.21))[0]
lat_region = lat[lat_idx]
lon_region = lon[lon_idx]

# Create output directory
os.makedirs('output', exist_ok=True)

# Create mhw_mask.nc with dimensions (time, lat, lon)
mhw = cell_mhw.astype(np.uint8)

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw)
    },
    coords={
        'time': np.array(target_dates, dtype='datetime64[ns]'),
        'lat': lat_region,
        'lon': lon_region,
    }
)

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Verify
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"Variables: {list(ds_check.variables)}")
print(f"Dimensions: {dict(ds_check.dims)}")
print(f"mhw shape: {ds_check.mhw.shape}")
print(f"mhw dtype: {ds_check.mhw.dtype}")
print(f"time: {ds_check.time.values[0]} to {ds_check.time.values[-1]}")
print(f"lat: {ds_check.lat.values[0]} to {ds_check.lat.values[-1]}, count: {len(ds_check.lat)}")
print(f"lon: {ds_check.lon.values[0]} to {ds_check.lon.values[-1]}, count: {len(ds_check.lon)}")
print(f"mhw sum: {ds_check.mhw.values.sum()}")
print(f"mhw max: {ds_check.mhw.values.max()}")
ds_check.close()
