import numpy as np, datetime
doy_ext = np.load('doy_ext.npy')
sizes = {d: int((np.abs(doy_ext.astype(int)-d)<=5).sum()) for d in range(1,367) if d!=60}
mx = max(sizes.values())
big = [d for d,s in sizes.items() if s==mx]
print('max pool size', mx, 'at doys', big)
d = big[0]
start_ext = datetime.date(1991,12,27)
sel = np.where(np.abs(doy_ext.astype(int)-d)<=5)[0]
import collections
per_year = collections.Counter()
for i in sel:
    dt = start_ext + datetime.timedelta(days=int(i))
    per_year[dt.year]+=1
print('per-year counts for doy', d, dict(per_year))
# count leap years 1992-2002
leaps = [y for y in range(1992,2003) if (y%4==0 and y%100!=0) or y%400==0]
print('leap years', leaps)
