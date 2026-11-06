import fsspec, h5py, numpy as np, time as tm
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
h = h5py.File(f, 'r')
tv = h['time'][:]
epoch = np.datetime64('1981-01-01')
dates = epoch + (tv.astype('int64') * 1_000_000_000).astype('timedelta64[ns]')
print('first/last:', dates[0], dates[-1], 'n=', len(dates))
dd = dates.astype('datetime64[D]').astype('int64')
print('daily contiguous:', np.all(np.diff(dd) == 1))
np.save('/tmp/dates.npy', dates.astype('datetime64[D]'))

# Benchmark: full plane read
t0 = tm.time()
plane = h['analysed_sst'][0, :, :]
print('full plane read: %.2fs' % (tm.time()-t0), plane.shape, plane.dtype)

# Benchmark: region hyperslab read for one day
t0 = tm.time()
reg = h['analysed_sst'][0, 45:105, 463:523]
print('region slab read: %.2fs' % (tm.time()-t0), reg.shape)
t0 = tm.time()
reg = h['analysed_sst'][0:10, 45:105, 463:523]
print('region slab 10 days: %.2fs' % (tm.time()-t0))
t0 = tm.time()
reg = h['analysed_sst'][0:50, 45:105, 463:523]
print('region slab 50 days: %.2fs' % (tm.time()-t0))
