import fsspec, h5py, numpy as np, time as tm
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
h = h5py.File(f, 'r')
print('root keys:', list(h.keys()))
t = h['time']
print('time attrs:', dict(t.attrs))
tv = t[:]
print('raw first/last:', tv[:3], tv[-3:], tv.dtype)
units = t.attrs['units']
if isinstance(units, bytes): units = units.decode()
print('units:', units)
epoch = np.datetime64(units.split('since')[1].strip().split()[0])
dates = epoch + tv.astype('timedelta64[D]')
print('decoded first/last:', dates[0], dates[-1], 'n=', len(dates))
# continuity check
dd = dates.astype('datetime64[D]').astype('int64')
print('daily contiguous:', np.all(np.diff(dd) == 1))

# check fs caching config
print('fs type:', type(fs))
try:
    print('fs kwargs:', {k: v for k, v in fs.kwargs.items()} if hasattr(fs,'kwargs') else 'n/a')
except Exception as e:
    print('kwargs err', e)
