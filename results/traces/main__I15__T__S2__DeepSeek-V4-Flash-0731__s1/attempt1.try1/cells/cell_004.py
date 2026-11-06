
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Check the region bounds
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

# Find grid indices
lat_sel = ds.latitude[(ds.latitude >= lat_min) & (ds.latitude <= lat_max)]
lon_sel = ds.longitude[(ds.longitude >= lon_min) & (ds.longitude <= lon_max)]
print('Latitude range:', lat_sel.values[0], lat_sel.values[-1], 'count:', len(lat_sel))
print('Longitude range:', lon_sel.values[0], lon_sel.values[-1], 'count:', len(lon_sel))

# Target period
import pandas as pd
target_start = '2019-06-01'
target_end = '2019-08-31'
time_sel = ds.time[(ds.time >= target_start) & (ds.time <= target_end)]
print('Time range:', time_sel.values[0], time_sel.values[-1], 'count:', len(time_sel))

# Baseline
base_start = '1992-01-01'
base_end = '2002-12-31'
# Plus extended baseline for window
ext_start = '1991-12-27'
ext_end = '2003-01-05'
time_base = ds.time[(ds.time >= ext_start) & (ds.time <= ext_end)]
print('Baseline time count:', len(time_base))
