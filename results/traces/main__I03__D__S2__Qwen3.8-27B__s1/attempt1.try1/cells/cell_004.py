import time, fsspec
fs = fsspec.filesystem('onedata')
t0 = time.time()
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
dt = time.time() - t0
import os
print("size:", os.path.getsize('/work/sst_s2.nc'))
print("elapsed: %.1f s" % dt)
