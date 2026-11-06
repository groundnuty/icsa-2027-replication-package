import numpy as np, datetime, json

c1 = np.load('chunk1.npy'); c2 = np.load('chunk2.npy'); c3 = np.load('chunk3.npy'); tgt = np.load('target.npy')
print(c1.shape, c2.shape, c3.shape, tgt.shape)
base_ext = np.concatenate([c1, c2, c3], axis=0).astype(np.float64)
print('base_ext', base_ext.shape)

start_ext = datetime.date(1991,12,27)
dates_ext = [start_ext + datetime.timedelta(days=k) for k in range(base_ext.shape[0])]
print('first/last ext:', dates_ext[0], dates_ext[-1])

def doy_of(d):
    yday = d.timetuple().tm_yday
    leap = (d.year % 4 == 0 and d.year % 100 != 0) or (d.year % 400 == 0)
    if not leap and yday >= 60:
        return yday + 1
    return yday

doy_ext = np.array([doy_of(d) for d in dates_ext])
print('doy range', doy_ext.min(), doy_ext.max(), 'len', len(doy_ext))
# checks
import collections
# 1991-12-27 should be 362; 1992-02-29 -> 60; 1993 has no 60; 2002-12-31 -> 366; 2003-01-05 -> 5
def show(ds):
    i = (datetime.date(ds.year,ds.month,ds.day) - start_ext).days
    print(ds, '->', doy_ext[i])
for ds in [datetime.date(1991,12,27), datetime.date(1991,12,31), datetime.date(1992,1,1),
           datetime.date(1992,2,28), datetime.date(1992,2,29), datetime.date(1992,3,1),
           datetime.date(1993,2,28), datetime.date(1993,3,1), datetime.date(1996,2,29),
           datetime.date(2002,12,31), datetime.date(2003,1,1), datetime.date(2003,1,5)]:
    show(ds)
# each doy 1..366 except 60 should appear 11 times (1992..2002) or so; 60: 3 times
cnt = collections.Counter(doy_ext.tolist())
print('doy 1 count', cnt[1], 'doy 60 count', cnt[60], 'doy 61 count', cnt[61], 'doy 366 count', cnt[366])
missing = [d for d in range(1,367) if cnt[d]==0]
print('missing doys in ext:', missing)
np.save('base_ext.npy', base_ext)
np.save('doy_ext.npy', doy_ext)
