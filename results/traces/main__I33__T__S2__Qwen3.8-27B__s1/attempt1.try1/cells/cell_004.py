import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf", decode_times=False, mask_and_scale=False)
v = ds['analysed_sst']
print(v.dtype)
print(v.attrs)
print('chunking:', v.encoding.get('chunksizes'))
print('encoding:', v.encoding)
# coords raw
print(ds['latitude'][:3].values, ds['latitude'][-3:].values)
print(ds['longitude'][:3].values, ds['longitude'][-3:].values)
print(ds['time'][:3].values, ds['time'][-3:].values)
print(ds.attrs.get('comment'))
print(ds.attrs.get('references'))
