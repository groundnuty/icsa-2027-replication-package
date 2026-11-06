import fsspec, re, datetime as dt
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
print(len(names))
other=[n for n in names if not re.match(r'sst_\d{8}\.nc$',n)]
print(other[:20], len(other))
dates=sorted(re.findall(r'sst_(\d{8})\.nc',' '.join(names)))
print(dates[0],dates[-1],len(dates))
allds=set(dates)
exp=[];d=dt.date(1991,12,27)
while d<=dt.date(2008,8,31):
    exp.append(d.strftime('%Y%m%d')); d+=dt.timedelta(1)
miss=[e for e in exp if e not in allds]
print(len(miss), miss[:20])