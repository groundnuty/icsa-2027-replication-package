import numpy as np, datetime
doy_ext = np.load('doy_ext.npy')
mx = max(int((np.abs(doy_ext.astype(int)-d)<=5).sum()) for d in range(1,367) if d!=60)
big = [d for d in range(1,367) if d!=60 and int((np.abs(doy_ext.astype(int)-d)<=5).sum())==mx]
print('max pool size', mx, 'at doys', big)
d=361
start_ext = datetime.date(1991,12,27)
import collections
sel = np.where(np.abs(doy_ext.astype(int)-d)<=5)[0]
per_year = collections.Counter()
for i in sel:
    dt = start_ext + datetime.timedelta(days=int(i))
    per_year[dt.year]+=1
print('per-year counts for doy 361:', dict(per_year))
# interior pool size = 11*11 = 121; max = 121+5 (year with 29 Feb +1, plus 2003 5-day tail) = 126 -> doy 6 near start tail; doy 361 near leap+tail? tail of 2003 at doy 5... |5-361|? no. Hmm check doy 361 pool composition
