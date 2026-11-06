import fsspec, os, time
os.makedirs('/work/output', exist_ok=True)
fs = fsspec.filesystem('onedata')
remote = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
t0 = time.time()
fs.get(remote, '/work/sst_s2.nc')
print("downloaded in", time.time()-t0, "seconds")
print("size:", os.path.getsize('/work/sst_s2.nc'))
