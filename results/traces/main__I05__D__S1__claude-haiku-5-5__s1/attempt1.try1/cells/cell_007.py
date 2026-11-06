import fsspec, os, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
t=time.time()
fs.get(base+'sst_19920101.nc','/work/b.nc')
print(time.time()-t, os.path.getsize('/work/b.nc'))