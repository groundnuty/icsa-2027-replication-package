import h5py, numpy as np, fsspec, datetime as dt

f = h5py.File('/work/tmp/one.nc','r')
lat = f['latitude'][:].astype(np.float64)
lon = f['longitude'][:].astype(np.float64)
tv = f['time'][:]
print('time value:', tv, '-> date:', dt.date(1981,1,1)+dt.timedelta(seconds=int(tv[0])))
print('lat[0], lat[-1], lat step:', lat[0], lat[-1], np.unique(np.diff(lat))[:5])
print('lon[0], lon[-1], lon step:', lon[0], lon[-1], np.unique(np.diff(lon))[:5])

lat_min, lat_max, lon_min, lon_max = 63.31, 64.51, 21.31, 22.51
latmask = (lat >= lat_min-1e-6) & (lat <= lat_max+1e-6)
lonmask = (lon >= lon_min-1e-6) & (lon <= lon_max+1e-6)
i0,i1 = np.where(latmask)[0][[0,-1]]
j0,j1 = np.where(lonmask)[0][[0,-1]]
print('lat indices', i0, i1, 'n=', latmask.sum(), 'values', lat[i0], lat[i1])
print('lon indices', j0, j1, 'n=', lonmask.sum(), 'values', lon[j0], lon[j1])
# check all selected coords are monotone and step uniform
print('lat selected first/last/steps uniq:', lat[i0:i1+1][0], lat[i0:i1+1][-1], np.unique(np.round(np.diff(lat[i0:i1+1]),9)))
print('lon selected first/last/steps uniq:', lon[j0:j1+1][0], lon[j0:j1+1][-1], np.unique(np.round(np.diff(lon[j0:j1+1]),9)))
# also check with float32 raw comparisons (no tolerance)
lat32 = f['latitude'][:]; lon32 = f['longitude'][:]
print('float32 strict count:', int(((lat32>=np.float32(63.31))&(lat32<=np.float32(64.51))).sum()), int(((lon32>=np.float32(21.31))&(lon32<=np.float32(22.51))).sum()))
f.close()

# check existence of edge files
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/sst_%Y%m%d.nc'
for d in ['1991-12-27','1991-12-31','1992-01-01','1992-02-29','1996-02-29','2000-02-29','2002-12-31','2003-01-05','2004-06-01','2004-08-31','2004-02-29']:
    try:
        date = dt.date.fromisoformat(d)
        p = date.strftime('icsa2027_data_20261101T090944Z/s1z/sst_%Y%m%d.nc')
        print(d, fs.exists(p))
    except Exception as e:
        print(d,'ERR',e)
