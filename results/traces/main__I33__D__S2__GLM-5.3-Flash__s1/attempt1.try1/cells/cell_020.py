import numpy as np
mask = np.load('/work/mask.npy')
active = mask.any(axis=(1,2))
cnt = mask.sum(axis=(1,2))
import xarray as xr
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
d = ds.time.sel(time=slice('2014-06-01','2014-08-31')).values
for k in range(92):
    if cnt[k] > 0 or (15 <= k <= 75):
        pass
# compact summary: first/last active day, counts around boundaries
ia = np.where(active)[0]
print('active day indices:', ia[0], '..', ia[-1], '| all consecutive:', np.all(np.diff(ia)==1), '| n=', len(ia))
print('dates:', str(d[ia[0]])[:10], '->', str(d[ia[-1]])[:10])
print('cells in MHW per day (nonzero days):')
nz = np.where(cnt>0)[0]
print(' '.join('%s:%d' % (str(d[k])[5:10], cnt[k]) for k in nz))
print('max cells in MHW on a day:', cnt.max(), 'of', 3290)