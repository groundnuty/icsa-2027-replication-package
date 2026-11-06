import xarray as xr
import numpy as np, time, inspect
import h5netcdf

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# check the underlying file format
with open(path, 'rb') as f:
    magic = f.read(8)
print("magic:", magic)

# time index mapping
t = ds.time.values
t0 = np.datetime64('1991-12-27')
t1 = np.datetime64('2003-01-05')
t2 = np.datetime64('2012-06-01')
t3 = np.datetime64('2012-08-31')
print("baseline window idx:", np.searchsorted(t, t0), np.searchsorted(t, t1, side='right')-1)
print("target idx:", np.searchsorted(t, t2), np.searchsorted(t, t3, side='right')-1)

# latitude / longitude indices for region
lat = ds.latitude.values
lon = ds.longitude.values
il = np.where((lat >= 62.25) & (lat <= 63.45))[0]
jl = np.where((lon >= 18.73) & (lon <= 19.93))[0]
print("lat idx", il.min(), il.max(), "vals", lat[il.min()], lat[il.max()], "count", len(il))
print("lon idx", jl.min(), jl.max(), "vals", lon[jl.min()], lon[jl.max()], "count", len(jl))
print("contiguous idx:", np.array_equal(il, np.arange(il.min(), il.max()+1)), np.array_equal(jl, np.arange(jl.min(), jl.max()+1)))
