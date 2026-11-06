
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20150601.nc', 'rb')
t0 = time.time()
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds['analysed_sst'].attrs)
a = ds['analysed_sst'].values
lat = ds['latitude'].values; lon = ds['longitude'].values
print('lat range', lat.min(), lat.max(), 'lon range', lon.min(), lon.max())
print('dtypes', a.dtype, lat.dtype, lon.dtype)
# region slices
latm = (lat >= 56.13 - 1e-6) & (lat <= 57.33 + 1e-6)
lonm = (lon >= 17.71 - 1e-6) & (lon <= 18.91 + 1e-6)
print('n lat', latm.sum(), 'n lon', lonm.sum())
print('lat vals', lat[latm][[0,1,-2,-1]], 'lon vals', lon[lonm][[0,1,-2,-1]])
sub = a[0][latm][:, lonm]
print('sub shape', sub.shape, 'finite frac', np.isfinite(sub).mean(), 'min/max', np.nanmin(sub), np.nanmax(sub))
ds.close(); f.close()
print('read time s:', time.time()-t0)
