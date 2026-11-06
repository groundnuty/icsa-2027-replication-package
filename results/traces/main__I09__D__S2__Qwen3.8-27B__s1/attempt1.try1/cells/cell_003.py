import time, fsspec
fs = fsspec.filesystem('onedata')
t0 = time.time()
local = '/work/sst_s2.nc'
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', local)
print("downloaded in", round(time.time()-t0,1), "s")
