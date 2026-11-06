import fsspec, os, re, collections, datetime
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(files))
names=[os.path.basename(f) for f in files]
print(collections.Counter(re.sub(r'\d','#',n) for n in names))
dates=sorted(n[4:12] for n in names if re.match(r'sst_\d{8}\.nc$',n))
print(len(dates), dates[0], dates[-1])
alld=set(dates); exp=[]
d=datetime.date(1982,1,1)
while d<=datetime.date(2022,12,31):
    exp.append(d.strftime('%Y%m%d')); d+=datetime.timedelta(1)
miss=[e for e in exp if e not in alld]
print('missing', len(miss), miss[:20])
print([n for n in names if not re.match(r'sst_\d{8}\.nc$',n)][:10])