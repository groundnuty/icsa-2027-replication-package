import fsspec, time, os
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/dl', exist_ok=True)
# batch test of 200 baseline files
import datetime as dt
d0 = dt.date(1992,1,1)
names = []
for i in range(200):
    names.append((p + f'/sst_{(d0+dt.timedelta(days=i)):%Y%m%d}.nc'))
t0=time.time()
fs.get(names, '/work/dl/')
t1=time.time()
n = len([f for f in os.listdir('/work/dl') if f.endswith('.nc')])
print('downloaded', n, 'files in', round(t1-t0,2), 's ->', round(200/(t1-t0),1), 'files/s')
