import os, re, datetime as dt
d = '/data/icsa2027_data_20261101T090944Z/s1z'
files = os.listdir(d)
print('n files:', len(files))
pat = re.compile(r'^sst_(\d{8})\.nc$')
dates = []
bad = []
for f in files:
    m = pat.match(f)
    if m:
        dates.append(m.group(1))
    else:
        bad.append(f)
print('bad names:', bad[:10], 'count', len(bad))
dates = sorted(dates)
print('first', dates[0], 'last', dates[-1])
ds = set(dates)
# check needed ranges
def daterange(a, b):
    cur = a
    while cur <= b:
        yield cur
        cur += dt.timedelta(days=1)
ext = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))
tgt = list(daterange(dt.date(2004,6,1), dt.date(2004,8,31)))
miss_ext = [x for x in ext if x.strftime('%Y%m%d') not in ds]
miss_tgt = [x for x in tgt if x.strftime('%Y%m%d') not in ds]
print('ext needed', len(ext), 'missing', len(miss_ext), miss_ext[:10])
print('tgt needed', len(tgt), 'missing', len(miss_tgt), miss_tgt[:10])
# extra files outside ext?
extra = [x for x in dates if x < '19911227' or (x > '20030105' and x < '20040601') or x > '20040831']
print('files outside needed ranges:', len(extra), extra[:5], extra[-5:] if extra else '')
import numpy as np, h5py, xarray
print('numpy', np.__version__, 'h5py', h5py.__version__, 'xarray', xarray.__version__)
print('cwd', os.getcwd(), 'writable', os.access(os.getcwd(), os.W_OK))
