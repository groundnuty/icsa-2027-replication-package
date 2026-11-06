import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20210615.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values.astype('float64')
    lon = ds['longitude'].values.astype('float64')
    sst = ds['analysed_sst'].values[0].astype('float64')

def dlat(v):  # index of value closest (they should be exact grid values)
    return int(np.argmin(np.abs(lat - v)))

for v in [56.09, 56.11, 56.13, 57.27, 57.29, 56.29]:
    print('lat', v, '->', lat[np.argmin(np.abs(lat - v))])
for v in [10.55, 10.57, 11.73, 11.75, 11.77]:
    print('lon', v, '->', lon[np.argmin(np.abs(lon - v))])

i_lat = np.where((lat >= 56.09 - 1e-9) & (lat <= 57.29 + 1e-9))[0]
i_lon = np.where((lon >= 10.55 - 1e-9) & (lon <= 11.75 + 1e-9))[0]
print('lat idx range:', i_lat.min(), i_lat.max(), 'count', len(i_lat))
print('lon idx range:', i_lon.min(), i_lon.max(), 'count', len(i_lon))
print('lat values ends:', lat[i_lat[0]], lat[i_lat[-1]])
print('lon values ends:', lon[i_lon[0]], lon[i_lon[-1]])
print('subgrid shape:', len(i_lat), 'x', len(i_lon))

sub = sst[np.ix_(i_lat, i_lon)]
fin = np.isfinite(sub)
print('finite fraction:', fin.mean())
print('cols fully finite (sea cells):', fin.all(axis=0).sum(), 'of', fin.shape[1])
print('rows fully finite:', fin.all(axis=1).sum())