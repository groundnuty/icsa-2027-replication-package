import xarray as xr, fsspec, numpy as np
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(p, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v = ds.analysed_sst
print('attrs:', v.attrs)
print('encoding:', {k: v.encoding.get(k) for k in ['dtype','_FillValue','scale_factor','add_offset','chunksizes','contiguous']})
print('chunks (xarray):', v.chunks)
print('dims:', v.dims, 'shape:', v.shape)
print('time dtype:', ds.time.dtype, 'first/last:', ds.time.values[0], ds.time.values[-1])
print('lat dtype:', ds.latitude.dtype, 'lon dtype:', ds.longitude.dtype)
print('lat[0:5]:', ds.latitude.values[:5], 'lat[-3:]', ds.latitude.values[-3:])
print('lon[0:5]:', ds.longitude.values[:5], 'lon[-3:]', ds.longitude.values[-3:])
