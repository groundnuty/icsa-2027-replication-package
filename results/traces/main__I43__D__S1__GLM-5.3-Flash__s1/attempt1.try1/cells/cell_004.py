import fsspec, os, time
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/test', exist_ok=True)
t0 = time.time()
fs.get(p + '/sst_20170601.nc', '/work/test/sst_20170601.nc')
t1 = time.time()
print('one file took', round(t1-t0,2), 's, size', os.path.getsize('/work/test/sst_20170601.nc'))
# test batch get with a list
t0 = time.time()
paths = [p + f'/sst_2017060{d}.nc' for d in range(2,6)]
fs.get(paths, '/work/test/')
t1 = time.time()
print('batch of 4 took', round(t1-t0,2), 's')
print(sorted(os.listdir('/work/test')))
import shutil; print(shutil.disk_usage('/work'))
