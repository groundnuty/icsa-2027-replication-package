
import fsspec
import xarray as xr
import numpy as np
import datetime as dt

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544
n_lat, n_lon = 60, 60

# Load a few sample files to understand the data
# Check cell (0,0) - is it land or sea?
f = fs.open(f'{base_path}/sst_19920701.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
s = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()
print("1992-07-01 cell (0,0):", s[0,0])
print("1992-07-01 cell (30,30):", s[30,30])

f = fs.open(f'{base_path}/sst_19950101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
s = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()
print("1995-01-01 cell (0,0):", s[0,0])
print("1995-01-01 cell (30,30):", s[30,30])

# Check target
f = fs.open(f'{base_path}/sst_20170601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
s = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()
print("2017-06-01 cell (0,0):", s[0,0])
print("2017-06-01 cell (30,30):", s[30,30])

# Check what cell (0,0) corresponds to in lat/lon
f = fs.open(f'{base_path}/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print("lat(0):", ds.latitude.values[lat_start], "lon(0):", ds.longitude.values[lon_start])
print("lat(30):", ds.latitude.values[lat_start+30], "lon(30):", ds.longitude.values[lon_start+30])
ds.close()

# Let me check what fraction of baseline values are NaN per cell
f = fs.open(f'{base_path}/sst_19920101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
s = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()
print("\n1992-01-01 NaN count:", np.isnan(s).sum(), "out of", 60*60)
