import fsspec, os, time
fs = fsspec.filesystem('onedata')
remote = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local = '/work/sst_s2.nc'
t0 = time.time()
fs.get(remote, local)
print('downloaded in', time.time()-t0, 's; size', os.path.getsize(local))
