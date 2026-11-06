import fsspec, xarray as xr, numpy as np, h5py, time
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
print('numpy', np.__version__)
ds = xr.open_dataset(f, engine='h5netcdf')
enc = ds.analysed_sst.encoding
for k in ['chunksizes','compression','compression_opts','scale_factor','add_offset','_FillValue','dtype','source']:
    print(k, '=', enc.get(k))
print('units attr:', ds.analysed_sst.attrs.get('units'))
print('valid_min/max:', ds.analysed_sst.attrs.get('valid_min'), ds.analysed_sst.attrs.get('valid_max'))

lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
latm = (lat >= 54.39) & (lat <= 55.59); lonm = (lon >= 18.25) & (lon <= 19.45)
print('lat idx', np.where(latm)[0][0], np.where(latm)[0][-1], 'n=', latm.sum())
print('lon idx', np.where(lonm)[0][0], np.where(lonm)[0][-1], 'n=', lonm.sum())
print('lat vals first/last in region:', lat[latm][:3], lat[latm][-3:])
print('lon vals first/last in region:', lon[lonm][:3], lon[lonm][-3:])

# raw h5py look
f2 = fs.open(path, 'rb')
h = h5py.File(f2, 'r')
def show(name, obj):
    if isinstance(obj, h5py.Dataset):
        print(name, obj.shape, obj.dtype, 'chunks', obj.chunks, 'compress', obj.compression, obj.compression_opts)
h.visititems(show)
