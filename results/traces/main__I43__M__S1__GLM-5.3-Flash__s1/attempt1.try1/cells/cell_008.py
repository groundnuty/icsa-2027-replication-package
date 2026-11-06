import h5py, numpy as np, xarray as xr
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc'
with h5py.File(p,'r') as f:
    v = f['analysed_sst']
    print('attrs:', dict(v.attrs))
    raw = v[0, 438:498, 487:547]
ds = xr.open_dataset(p, engine='h5netcdf')
xa = ds['analysed_sst'][0, 438:498, 487:547].values
print('raw nan count', np.isnan(raw).sum(), 'xarray nan count', np.isnan(xa).sum())
print('equal (nan-aware):', np.array_equal(np.nan_to_num(raw, nan=-999), np.nan_to_num(xa.astype('float32'), nan=-999)))
print('raw dtype', raw.dtype, 'min/max of finite:', np.nanmin(raw), np.nanmax(raw))
# coordinate consistency across files
lats=[]; lons=[]
for fn in ['sst_19820101.nc','sst_19921231.nc','sst_20030105.nc','sst_20170831.nc','sst_20231231.nc']:
    with h5py.File('/data/icsa2027_data_20261101T090944Z/s1z/'+fn,'r') as f:
        lats.append(f['latitude'][:].copy()); lons.append(f['longitude'][:].copy())
        print(fn, 'vars:', list(f.keys()))
same = all(np.array_equal(lats[0], a) and np.array_equal(lons[0], b) for a,b in zip(lats[1:],lons[1:]))
print('coords identical across files:', same)
# time variable check
with h5py.File('/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc','r') as f:
    print('time raw:', f['time'][:], dict(f['time'].attrs))
