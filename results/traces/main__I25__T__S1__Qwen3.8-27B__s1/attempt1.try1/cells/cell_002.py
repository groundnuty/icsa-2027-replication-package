
import fsspec
fs = fsspec.filesystem('onedata')
entries = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
files = sorted(e.split('/')[-1] for e in entries if e.endswith('.nc'))
print("count:", len(files))
print("first:", files[:3])
print("last:", files[-3:])
# check needed ranges
import datetime as dt
def in_range(f):
    d = dt.datetime.strptime(f[4:10],'%Y%m%d').date()
    return d
need = set()
# baseline 1992-01-01..2002-12-31 plus windows 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05
for i in range((dt.date(2003,1,5)-dt.date(1991,12,27)).days+1):
    d = dt.date(1991,12,27)+dt.timedelta(days=i)
    need.add(d)
# target 2016-06-01..2016-08-31
for i in range((dt.date(2016,8,31)-dt.date(2016,6,1)).days+1):
    d = dt.date(2016,6,1)+dt.timedelta(days=i)
    need.add(d)
have = {in_range(f) for f in files}
missing = sorted(need - have)
print("needed files:", len(need), "missing:", missing[:20], "n missing:", len(missing))
