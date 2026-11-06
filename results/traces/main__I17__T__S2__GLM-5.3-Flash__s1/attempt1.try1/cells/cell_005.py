import fsspec, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
print("opened ok", f)

import h5netcdf
ds = h5netcdf.File(f, 'r')
print("root keys:", list(ds.keys()))
v = ds['analysed_sst']
print("dims:", v.dimensions, "shape:", v.shape)
print("chunks:", v.chunks)
print("dtype:", v.dtype)
print("attrs:", dict(v.attrs))
tv = ds['time']
print("time dtype:", tv.dtype, "attrs:", dict(tv.attrs))
print("time[:3]:", np.asarray(tv[:3]), "time[-3:]", np.asarray(tv[-3:]))
lat = np.asarray(ds['latitude'][:])
lon = np.asarray(ds['longitude'][:])
print("lat:", lat[:3], lat[-3:])
print("lon:", lon[:3], lon[-3:])
ds.close()
