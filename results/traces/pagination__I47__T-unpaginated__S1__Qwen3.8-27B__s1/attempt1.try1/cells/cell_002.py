
import fsspec, re
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
names = [re.search(r'sst_(\d{8})\.nc$', f).group(1) for f in files if f.endswith('.nc')]
print("total files:", len(names))
print("min:", min(names), "max:", max(names))
# Check contiguity and missing days
from datetime import date, timedelta
d0 = date(int(names[0][:4]), int(names[0][4:6]), int(names[0][6:]))
d1 = date(int(names[-1][:4]), int(names[-1][4:6]), int(names[-1][6:]))
expected = set((d0 + timedelta(days=i)).strftime('%Y%m%d') for i in range((d1-d0).days+1))
missing = expected - set(names)
print("missing days:", sorted(missing)[:20], "count:", len(missing))
# Check needed files exist
needed = set()
from datetime import datetime
def days(y0,m0,d0,y1,m1,d1):
    cur = date(y0,m0,d0); end = date(y1,m1,d1)
    out=[]
    while cur<=end:
        out.append(cur); cur+=timedelta(days=1)
    return out
for a in days(1991,12,27,1992,1,5)+days(2002,12,26,2003,1,5)+days(2019,6,1,2019,8,31):
    needed.add(a.strftime('%Y%m%d'))
print("needed present:", all(n in set(names) for n in needed))
