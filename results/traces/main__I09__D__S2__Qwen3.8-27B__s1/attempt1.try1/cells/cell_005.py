import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
v = ds['analysed_sst']
print("var attrs:", dict(v.attrs))
print("comment:", v.attrs.get('comment'))
print()
t = ds.time.values
print("time dtype:", t.dtype)
print("first 3:", t[:3])
print("last 3:", t[-3:])
print()
lat = ds.latitude.values
lon = ds.longitude.values
print("lat dtype:", lat.dtype, "n=", len(lat), "min", lat.min(), "max", lat.max())
print("lon dtype:", lon.dtype, "n=", len(lon), "min", lon.min(), "max", lon.max())
print("lat diffs:", np.unique(np.diff(lat)))
print("lon diffs:", np.unique(np.diff(lon)))
print("time monotonic:", np.all(np.diff(t) > 0))
# check all timestamps at midnight
print("any non-midnight:", np.any(t.astype('datetime64[D]') != t))
ds.close()
