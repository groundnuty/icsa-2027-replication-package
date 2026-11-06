import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print()
print('dims:', dict(ds.sizes))
print('time[0], time[-1]:', str(ds.time.values[0])[:10], str(ds.time.values[-1])[:10], 'n=', ds.sizes['time'])
print('lat:', float(ds.lat.min()), float(ds.lat.max()), 'n=', ds.sizes['lat'])
print('lon:', float(ds.lon.min()), float(ds.lon.max()), 'n=', ds.sizes['lon'])
for v in ds.data_vars:
    print(v, ds[v].dtype, ds[v].encoding.get('_FillValue'), ds[v].attrs.get('units'), dict(ds[v].encoding).get('chunksizes'))
