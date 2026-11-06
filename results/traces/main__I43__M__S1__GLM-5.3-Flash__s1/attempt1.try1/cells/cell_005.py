import numpy as np, xarray as xr, time
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
lat = ds['latitude'].values.astype('float64')
lon = ds['longitude'].values.astype('float64')
lat_sel = (lat >= 62.25 - 1e-9) & (lat <= 63.45 + 1e-9)
lon_sel = (lon >= 18.73 - 1e-9) & (lon <= 19.93 + 1e-9)
# contiguous slices?
ilat = np.where(lat_sel)[0]; ilon = np.where(lon_sel)[0]
print('lat idx', ilat[0], ilat[-1], np.all(np.diff(ilat)==1))
print('lon idx', ilon[0], ilon[-1], np.all(np.diff(ilon)==1))
lat_sl = slice(ilat[0], ilat[-1]+1); lon_sl = slice(ilon[0], ilon[-1]+1)
sst = ds['analysed_sst'][0, lat_sl, lon_sl].values.astype('float64')
print('shape', sst.shape, 'nan frac', np.isnan(sst).mean())
t0=time.time()
for i in range(20):
    d = xr.open_dataset(f'/data/icsa2027_data_20261101T090944Z/s1z/sst_1992{str(1+i%12).zfill(2)}01.nc', engine='h5netcdf')
    v = d['analysed_sst'][0, lat_sl, lon_sl].values
    d.close()
print('20 files in', time.time()-t0, 's')
