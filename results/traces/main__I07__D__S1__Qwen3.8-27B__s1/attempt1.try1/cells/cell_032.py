import xarray as xr, numpy as np
lat_vals = np.load('/work/lat_vals.npy')
d = xr.open_dataset('/work/data/sst_19920601.nc', engine='h5netcdf')
la = d.latitude.values
print("lat dtype:", la.dtype, lat_vals.dtype)
target = lat_vals[30]
print("target:", target, repr(target))
print("match count:", (la == target).sum())
print("closest:", np.argmin(np.abs(la - target)), la[np.argmin(np.abs(la - target))])
# check all grid equal
d2 = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
print("grid identical 1992 vs 2021:", np.array_equal(d.latitude.values, d2.latitude.values), np.array_equal(d.longitude.values, d2.longitude.values))
d.close(); d2.close()
