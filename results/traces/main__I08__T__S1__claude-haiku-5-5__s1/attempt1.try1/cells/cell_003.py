import fsspec,re,datetime
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in files]
print(len(names))
pat=re.compile(r'^sst_(\d{8})\.nc$')
odd=[n for n in names if not pat.match(n)]
print(len(odd), odd[:20])
dates=sorted(pat.match(n).group(1) for n in names if pat.match(n))
print(dates[0], dates[-1], len(dates))
exp=[]
d=datetime.date(1991,12,27)
while d<=datetime.date(2007,8,31):
    exp.append(d.strftime('%Y%m%d')); d+=datetime.timedelta(1)
missing=sorted(set(exp)-set(dates))
print(len(exp), len(missing), missing[:20])