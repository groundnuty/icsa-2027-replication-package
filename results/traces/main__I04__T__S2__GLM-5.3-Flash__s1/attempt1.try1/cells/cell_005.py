import fsspec, h5py, numpy as np, time as tm, os

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
dates = np.load('/tmp/dates.npy')  # datetime64[D], 1982-01-01..2023-12-31
L0, L1 = 45, 105   # lat idx range (exclusive end)
O0, O1 = 463, 523  # lon idx range

i0 = int(np.searchsorted(dates, np.datetime64('1991-12-27')))
i1 = int(np.searchsorted(dates, np.datetime64('2003-01-05'))) + 1
print('window idx', i0, i1, 'n=', i1-i0, dates[i0], dates[i1-1])
# contiguity check
assert np.all(np.diff(dates[i0:i1].astype('int64')) == 1)

f = fs.open(path, 'rb')
h = h5py.File(f, 'r')
dset = h['analysed_sst']
win = np.empty((i1-i0, 60, 60), dtype=np.float32)
t0 = tm.time()
CH = 1000
for s in range(i0, i1, CH):
    e = min(s+CH, i1)
    win[s-i0:e-i0] = dset[s:e, L0:L1, O0:O1]
print('window read %.1fs' % (tm.time()-t0), win.shape)
np.save('/tmp/win.npy', win)
print('saved. nan frac in window: %.4f' % np.isnan(win).mean())
