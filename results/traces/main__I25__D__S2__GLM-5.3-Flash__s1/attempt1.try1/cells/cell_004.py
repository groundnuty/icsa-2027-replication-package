import h5py, numpy as np, time
f = h5py.File('/work/sst_s2.nc','r')
lat = f['latitude'][:].astype(np.float64)
lon = f['longitude'][:].astype(np.float64)
eps = 1e-5
latm = (lat >= 57.57-eps) & (lat <= 58.77+eps)
lonm = (lon >= 10.25-eps) & (lon <= 11.45+eps)
i0,i1 = np.flatnonzero(latm)[0], np.flatnonzero(latm)[-1]
j0,j1 = np.flatnonzero(lonm)[0], np.flatnonzero(lonm)[-1]
print('lat idx', i0, i1, 'n', i1-i0+1, 'lat range', lat[i0], lat[i1])
print('lon idx', j0, j1, 'n', j1-j0+1, 'lon range', lon[j0], lon[j1])
print('any interior gaps?', np.all(np.diff(np.flatnonzero(latm))==1), np.all(np.diff(np.flatnonzero(lonm))==1))

t = f['time'][:]
t64 = np.datetime64('1981-01-01T00:00:00') + t.astype('timedelta64[s]')
print('time[0]', t64[0], 'time[-1]', t64[-1], 'n', t64.size)
d = f['analysed_sst']
# benchmark 20 chunk reads
t0=time.time()
for i in range(5000, 5020):
    sl = d[i, i0:i1+1, j0:j1+1]
dt=time.time()-t0
print('20 slices in %.2fs -> est full read (4180 chunks): %.0fs' % (dt, dt/20*4180))
# check finiteness/typical values in region for one summer day
sl = d[12600, i0:i1+1, j0:j1+1]
print('day', t64[12600], 'finite frac', np.isfinite(sl).mean(), 'min/max', np.nanmin(sl), np.nanmax(sl))
f.close()
