
import fsspec
import xarray as xr
import numpy as np

# Get coordinates from the dataset
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat_full = ds['latitude'].values
lon_full = ds['longitude'].values

# Region indices
lat_idx = np.arange(157, 217)  # 60 cells
lon_idx = np.arange(562, 622)  # 60 cells

region_lat = lat_full[lat_idx]  # (60,)
region_lon = lon_full[lon_idx]  # (60,)

print('Region lat shape:', region_lat.shape)
print('Region lon shape:', region_lon.shape)
print('Region lat dtype:', region_lat.dtype)
print('Region lon dtype:', region_lon.dtype)

# Get time values for target period
# We need to read the time coordinate from the target files
# Each file has a single time value
from datetime import date, timedelta

target_dates = []
d = date(2008, 6, 1)
while d <= date(2008, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Read time from one file to check format
path2 = 'icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc'
f2 = fs.open(path2, 'rb')
ds2 = xr.open_dataset(f2, engine='h5netcdf')
print('Time value:', ds2['time'].values)
print('Time dtype:', ds2['time'].dtype)

# Get time values from files
times = []
for dt in target_dates:
    fname = f'sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc'
    p = f'icsa2027_data_20261101T090944Z/s1z/{fname}'
    f3 = fs.open(p, 'rb')
    ds3 = xr.open_dataset(f3, engine='h5netcdf')
    times.append(ds3['time'].values[0])
    if len(times) == 1:
        print('First time:', times[0])

times = np.array(times, dtype='datetime64[ns]')
print('Times shape:', times.shape)
print('First few times:', times[:3])
print('Last few times:', times[-3:])
print('Time dtype:', times.dtype)
