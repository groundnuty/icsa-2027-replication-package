import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
print('lat step', np.diff(lat)[:3], 'lon step', np.diff(lon)[:3])
latmin,latmax,lonmin,lonmax = 57.83,59.03,17.41,18.61
for name,arr,b0,b1 in [('lat',lat,latmin,latmax),('lon',lon,lonmin,lonmax)]:
    inside = np.where((arr>=b0)&(arr<=b1))[0]
    print(name,'n=',len(inside),'idx',inside[0],inside[-1],'vals',arr[inside[0]],arr[inside[-1]],
          'prev/next:', arr[inside[0]-1] if inside[0]>0 else None, arr[inside[-1]+1] if inside[-1]+1<len(arr) else None)
# check time daily regularity
t = ds.time.values
d = np.diff(t).astype('timedelta64[D]').astype(int)
print('diffs unique:', np.unique(d))
# baseline / target slices
tb = (ds.time >= np.datetime64('1992-01-01')) & (ds.time <= np.datetime64('2002-12-31'))
tt = (ds.time >= np.datetime64('2008-06-01')) & (ds.time <= np.datetime64('2008-08-31'))
print('nb', int(tb.sum()), 'nt', int(tt.sum()), 'first target', str(t[tt][0])[:10], 'last', str(t[tt][-1])[:10])
