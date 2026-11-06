import fsspec, xarray as xr, numpy as np, json

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

sst = ds['analysed_sst']
print("encoding:", {k: v for k, v in sst.encoding.items() if k != 'chunks'})
print("chunks (shape):", sst.encoding.get('chunks'))
print("chunksizes (h5py):", getattr(sst.data, 'chunks', None))

t = ds['time'].values
print("time dtype:", t.dtype, "n:", len(t))
d = np.diff(t).astype('timedelta64[ns]')
print("unique time steps:", np.unique(d))

lat = ds['latitude'].values.astype('float64')
lon = ds['longitude'].values.astype('float64')
print("lat[0], lat[-1]:", lat[0], lat[-1], "dl:", np.unique(np.diff(lat).round(6)))
print("lon[0], lon[-1]:", lon[0], lon[-1], "dl:", np.unique(np.diff(lon).round(6)))
print("t0:", t[0], "t-1:", t[-1])
