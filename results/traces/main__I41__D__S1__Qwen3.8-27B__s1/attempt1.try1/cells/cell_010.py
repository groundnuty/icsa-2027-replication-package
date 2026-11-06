import fsspec, os, numpy as np, xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
fs.get(base + '/sst_19920101.nc', '/work/dl/dbg.nc')
ds = xr.open_dataset('/work/dl/dbg.nc', engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
tval = ds['time'].values[0]
LAT = (np.arange(626) * 0.02 + 53.5)
LON = (np.arange(1051) * 0.02 + 9.0)
print("time:", tval, repr(tval))
print("lat dtype:", lat.dtype, "first/last:", lat[0], lat[-1])
print("lat equal to computed:", np.array_equal(lat, LAT))
diff = lat - LAT.astype(lat.dtype)
print("lat max abs diff:", np.abs(diff).max())
print("lon max abs diff:", np.abs((lon - LON.astype(lon.dtype))).max())
print(ds['latitude'].attrs, ds['time'].attrs)
print("encoding:", ds['latitude'].encoding)
