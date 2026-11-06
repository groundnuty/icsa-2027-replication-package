import numpy as np
from datetime import date, timedelta
ext = np.load('/work/ext.npy')  # dates 1991-12-27 .. 2003-01-05

def doy_of(y,m,d): return (date(2000,m,d) - date(2000,1,1)).days + 1
d0 = date(1992,1,1); d1 = date(2002,12,31)
base_dates = [d0 + timedelta(days=k) for k in range((d1-d0).days + 1)]
e0 = date(1991,12,27)
def eidx(dt): return (dt - e0).days

pool = {d: [] for d in range(1, 367)}
for b in base_dates:
    bd = doy_of(b.year, b.month, b.day)
    if bd == 60:          # no pool centred on 29 Feb
        continue
    for o in range(-5, 6):
        p = b + timedelta(days=o)
        pool[bd].append(eidx(p))   # NOTE: no filter on p's own doy -> 29 Feb values included in neighbours' pools

from collections import Counter
cnt = Counter(len(v) for v in pool.values() if v)
print('pool size histogram:', dict(cnt))
print('pool60:', len(pool[60]))
# verify 29 Feb presence in neighbours' pools
d029 = [eidx(date(y,2,29)) for y in (1992,1996,2000)]
for d in range(55, 66):
    if d == 60: continue
    inc = sum(i in pool[d] for i in d029)
    print('doy', d, 'size', len(pool[d]), 'leap-29Feb dates included:', inc)
# spot-check doy 1 and 366 date ranges
print('pool1 date range:', date(1991,12,27)+timedelta(days=min(pool[1])), '..', date(1991,12,27)+timedelta(days=max(pool[1])))
print('pool366 date range:', date(1991,12,27)+timedelta(days=min(pool[366])), '..', date(1991,12,27)+timedelta(days=max(pool[366])))
# check duplicates (windows overlapping?) - within a doy, windows from different years are 5+ days apart, no overlap
print('any duplicate indices in pools:', any(len(v)!=len(set(v)) for v in pool.values()))