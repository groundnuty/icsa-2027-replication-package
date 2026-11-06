import fsspec, xarray as xr, numpy as np, pandas as pd, json, os
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")

lat = ds.latitude.values; lon = ds.longitude.values
print("lat dtype", lat.dtype)
eps = 1e-9
lat_sel = (lat >= 61.57 - eps) & (lat <= 62.77 + eps)
lon_sel = (lon >= 20.17 - eps) & (lon <= 21.37 + eps)
li = np.where(lat_sel)[0]; lj = np.where(lon_sel)[0]
print("n lat:", len(li), li[0], li[-1], lat[li[0]], lat[li[-1]])
print("n lon:", len(lj), lj[0], lj[-1], lon[lj[0]], lon[lj[-1]])
# check exact grid values
print("lats:", lat[li[:3]], lat[li[-3:]])
print("lons:", lon[lj[:3]], lon[lj[-3:]])
print("unique lat step:", np.unique(np.diff(lat)))
print("unique lon step:", np.unique(np.diff(lon)))
