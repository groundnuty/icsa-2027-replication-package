import numpy as np, xarray as xr, fsspec
print("numpy", np.__version__, "xarray", xr.__version__)
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds['analysed_sst']
print("encoding:", sst.encoding.get('_FillValue'), sst.dtype, sst.dims)

lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat range", lat.min(), lat.max(), "step", lat[1]-lat[0])
print("lon range", lon.min(), lon.max(), "step", lon[1]-lon[0])

latmask = (lat >= 54.13) & (lat <= 55.33)
lonmask = (lon >= 14.67) & (lon <= 15.87)
print("n lat", latmask.sum(), "n lon", lonmask.sum())
print("lat sel:", lat[latmask][:3], "...", lat[latmask][-3:])
print("lon sel:", lon[lonmask][:3], "...", lon[lonmask][-3:])

t = ds['time'].values
print("time0", t[0], "time-1", t[-1], "n", len(t))
d = np.diff(t).astype('timedelta64[D]')
print("all daily 1-day steps:", np.all(d == np.timedelta64(1,'D')))
