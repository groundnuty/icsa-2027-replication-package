import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

with fs.open(f'{base}/sst_20040615.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values.astype(np.float64)
    lon = ds['longitude'].values.astype(np.float64)
    ds.close()

print("lat first/last:", lat[:3], lat[-3:], "step:", np.diff(lat)[:3], np.unique(np.round(np.diff(lat),6)))
print("lon first/last:", lon[:3], lon[-3:], "step:", np.diff(lon)[:3])

lat_min, lat_max, lon_min, lon_max = 54.17, 55.37, 13.25, 14.45
eps = 1e-6
ii = np.where((lat >= lat_min-eps) & (lat <= lat_max+eps))[0]
jj = np.where((lon >= lon_min-eps) & (lon <= lon_max+eps))[0]
print("lat idx:", ii[0], ii[-1], "n=", ii.size, "vals", lat[ii[0]], lat[ii[-1]])
print("lon idx:", jj[0], jj[-1], "n=", jj.size, "vals", lon[jj[0]], lon[jj[-1]])
