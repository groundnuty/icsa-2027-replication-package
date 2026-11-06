import fsspec, h5py, numpy as np, os, json, xarray as xr

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
h = h5py.File(f, 'r')
lat_all = h['latitude'][:]; lon_all = h['longitude'][:]
lat_reg = lat_all[45:105].astype(np.float64)   # exact dataset values
lon_reg = lon_all[463:523].astype(np.float64)
print('lat_reg[:3]', lat_reg[:3], 'lat_reg[-3:]', lat_reg[-3:])
print('lon_reg[:3]', lon_reg[:3], 'lon_reg[-3:]', lon_reg[-3:])
np.save('/tmp/lat_reg.npy', lat_reg); np.save('/tmp/lon_reg.npy', lon_reg)

# also inspect raw structure of the file we wrote
w = h5py.File('/work/output/mhw_mask.nc', 'r')
m = w['mhw']
print('written mhw:', m.shape, m.dtype, 'chunks', m.chunks, 'attrs:', dict(m.attrs))
print('fillvalue attr present:', '_FillValue' in m.attrs)
print('lat dtype in written file:', w['lat'][:].dtype)
w.close()
