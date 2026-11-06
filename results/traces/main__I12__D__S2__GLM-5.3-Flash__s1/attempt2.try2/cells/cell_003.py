import xarray as xr, numpy as np, datetime as dt
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values; t = ds.time.values
print('lat step', np.diff(lat)[:3], 'monotonic up:', np.all(np.diff(lat)>0))
print('lon step', np.diff(lon)[:3], 'monotonic up:', np.all(np.diff(lon)>0))
print('lat range', lat.min(), lat.max())
print('lon range', lon.min(), lon.max())
lat_mask = (lat >= 56.09) & (lat <= 57.29)
lon_mask = (lon >= 10.55) & (lon <= 11.75)
print('nlat', lat_mask.sum(), lat[lat_mask][0], lat[lat_mask][-1])
print('nlon', lon_mask.sum(), lon[lon_mask][0], lon[lon_mask][-1])
# check times daily complete
diffs = np.diff(t).astype('timedelta64[D]').astype(int)
print('all daily:', np.all(diffs==1), 'span', str(t[0])[:10], str(t[-1])[:10])
# check exact years present
years = {str(pd)[:4] for pd in t}
print(sorted(years)[:5], sorted(years)[-5:])
# check encoding of analysed_sst
print(ds.analysed_sst.encoding)