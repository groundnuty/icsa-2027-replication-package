import fsspec, h5py, numpy as np, time as tm, os

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
dates = np.load('/tmp/dates.npy')
L0, L1 = 45, 105
O0, O1 = 463, 523

t0i = int(np.searchsorted(dates, np.datetime64('2020-06-01')))
t1i = int(np.searchsorted(dates, np.datetime64('2020-08-31'))) + 1
print('target idx', t0i, t1i, 'n=', t1i-t0i, dates[t0i], dates[t1i-1])
assert np.all(np.diff(dates[t0i:t1i].astype('int64')) == 1)

f = fs.open(path, 'rb')
h = h5py.File(f, 'r')
dset = h['analysed_sst']
tgt = dset[t0i:t1i, L0:L1, O0:O1].astype(np.float64)
print('target read %.1fs' % (tm.time()-t0), tgt.shape)
np.save('/tmp/tgt.npy', tgt)
print('target nan frac: %.4f' % np.isnan(tgt).mean())
