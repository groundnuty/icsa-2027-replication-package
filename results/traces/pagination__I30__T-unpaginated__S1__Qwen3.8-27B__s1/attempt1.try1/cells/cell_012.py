
import fsspec, xarray, numpy as np, datetime as dt
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc','rb')
ds = xarray.open_dataset(f, engine='h5netcdf')
lat = ds['latitude'].values.astype(float64 if False else 'float64')
lon = ds['longitude'].values.astype('float64')
print('lat range', lat.min(), lat.max(), len(lat), lat[:3], lat[-3:])
print('lon range', lon.min(), lon.max(), len(lon), lon[:3], lon[-3:])
# check step
print('dlat', np.diff(lat).min(), np.diff(lat).max())
li = np.where((lat >= 58.69 - 1e-6) & (lat <= 59.89 + 1e-6))[0]
lj = np.where((lon >= 18.69 - 1e-6) & (lon <= 19.89 + 1e-6))[0]
print('n lat cells:', len(li), li[0], li[-1], lat[li[0]], lat[li[-1]])
print('n lon cells:', len(lj), lj[0], lj[-1], lon[lj[0]], lon[lj[-1]])
# sanity: values around 58.69
for v in [58.68, 58.70, 59.88, 59.90]:
    k = np.argmin(np.abs(lat-v)); print(v, '->', lat[k])
ds.close(); f.close()
