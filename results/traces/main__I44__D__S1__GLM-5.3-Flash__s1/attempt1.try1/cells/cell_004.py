import datetime as dt, fsspec, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
missing=[]
start=dt.date(1991,12,27); end=dt.date(2004,8,31)
d=start
paths=[]
while d<=end:
    paths.append((d, base+d.strftime('sst_%Y%m%d.nc')))
    d+=dt.timedelta(days=1)
print('total dates spanned:', len(paths))
t0=time.time()
ex = [p for _,p in paths]
exists = [fs.exists(p) for p in ex]
t1=time.time()
print('exists-check seconds:', t1-t0)
for (d,p),e in zip(paths,exists):
    if not e: missing.append(d)
print('missing files:', len(missing))
print(missing[:80])
