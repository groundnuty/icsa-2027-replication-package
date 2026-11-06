import xarray as xr, numpy as np, time
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc'
t0=time.time()
ds = xr.open_dataset(p, engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values
print('open time', time.time()-t0)
print(lat[:5], lat[-3:], lon[:5], lon[-3:])
print('lat dtype', lat.dtype, 'lon dtype', lon.dtype)
# region selection
latmask = (lat >= 54.13) & (lat <= 55.33)
lonmask = (lon >= 14.67) & (lon <= 15.87)
ilat = np.where(latmask)[0]; ilon = np.where(lonmask)[0]
print('nlat', ilat.size, lat[ilat][[0,-1]], 'nlon', ilon.size, lon[ilon][[0,-1]])
t0=time.time()
sub = ds.analysed_sst.isel(time=0, latitude=ilat, longitude=ilon).values
print('read time', time.time()-t0, sub.shape, sub.dtype)
print('finite frac', np.isfinite(sub).mean(), 'min/max', np.nanmin(sub), np.nanmax(sub))
# check encoding
print(ds.analysed_sst.encoding)
