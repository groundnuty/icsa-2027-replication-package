import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
listing = fs.ls(path, detail=False)
print('n listed:', len(listing))
print('first:', listing[:3])
print('last:', listing[-3:])
# check needed dates exist
import datetime as dt
def fname(d): return f"{path}/sst_{d:%Y%m%d}.nc"
needed = []
d = dt.date(1991,12,27)
while d <= dt.date(2003,1,5):
    needed.append(d); d += dt.timedelta(days=1)
d = dt.date(2008,6,1)
tneed=[]
while d <= dt.date(2008,8,31):
    tneed.append(d); d += dt.timedelta(days=1)
missing = [f for f in [fname(x) for x in needed+tneed] if f not in set(listing)]
print('missing needed:', missing[:10], 'total missing:', len(missing))
