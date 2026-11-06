
import fsspec, datetime as dt, collections
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
have=set(n[4:12] for n in names)
need=[]
d=dt.date(1991,12,27)
while d<=dt.date(2003,1,5):
    need.append(d); d+=dt.timedelta(1)
d=dt.date(2013,6,1)
while d<=dt.date(2013,8,31):
    need.append(d); d+=dt.timedelta(1)
missing=[x for x in need if x.strftime('%Y%m%d') not in have]
print(len(need), len(missing), missing[:20])
print(min(have), max(have), len(have), len(names))
