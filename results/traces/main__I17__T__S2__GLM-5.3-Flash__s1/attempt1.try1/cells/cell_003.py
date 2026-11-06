import fsspec, xarray as xr, numpy as np

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf', decode_times=False)

sst = ds['analysed_sst']
print("encoding:", {k: v for k, v in sst.encoding.items()})
print("chunksizes:", getattr(sst.data, 'chunks', None))

lat = ds['latitude'].values.astype('float64')
lon = ds['longitude'].values.astype('float64')
print("lat0, latN:", lat[0], lat[-1], "uniq dl:", np.unique(np.diff(lat).round(6)))
print("lon0, lonN:", lon[0], lon[-1], "uniq dl:", np.unique(np.diff(lon).round(6)))
print("time raw[:5]:", ds['time'].values[:5], ds['time'].values[-3:])
print("time attrs:", ds['time'].attrs)
print("sst attrs:", sst.attrs)
