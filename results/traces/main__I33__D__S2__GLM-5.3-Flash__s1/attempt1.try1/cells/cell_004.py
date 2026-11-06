import numpy as np, h5py, time
f = h5py.File('/work/s2z/sst_s2.nc', 'r')
dset = f['analysed_sst']
import xarray as xr
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values

def tidx(datestr):
    return int(np.searchsorted(t, np.datetime64(datestr)))

i_e0, i_e1 = tidx('1991-12-27'), tidx('2003-01-05')+1
i_t0, i_t1 = tidx('2014-06-01'), tidx('2014-08-31')+1
print('ext idx', i_e0, i_e1, str(t[i_e0])[:10], str(t[i_e1-1])[:10])
print('tgt idx', i_t0, i_t1, str(t[i_t0])[:10], str(t[i_t1-1])[:10])

latm = (lat >= 59.05) & (lat <= 60.25); lonm = (lon >= 21.25) & (lon <= 22.45)
li = np.where(latm)[0]; oi = np.where(lonm)[0]
print('lat idx contiguous:', np.all(np.diff(li)==1), li[0], li[-1])
print('lon idx contiguous:', np.all(np.diff(oi)==1), oi[0], oi[-1])
ls, le = li[0], li[-1]+1; os_, oe = oi[0], oi[-1]+1

# timing test: 30 days
t0 = time.time()
_ = dset[i_t0:i_t0+30, ls:le, os_:oe]
dt = time.time()-t0
print('30-day read: %.2fs -> est full %.0fs' % (dt, dt/30*(i_e1-i_e0+i_t1-i_t0)))