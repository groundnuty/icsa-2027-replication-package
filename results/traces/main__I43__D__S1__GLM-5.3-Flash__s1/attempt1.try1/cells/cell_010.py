import fsspec, time, os, datetime as dt
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/dl2', exist_ok=True)
names = [p + f'/sst_{(dt.date(1992,1,1)+dt.timedelta(days=i)):%Y%m%d}.nc' for i in range(200,400)]
t0=time.time()
fs.get(names, '/work/dl2/')
t1=time.time()
print('200 more in', round(t1-t0,2), 's ->', round(200/(t1-t0),1), 'files/s')
