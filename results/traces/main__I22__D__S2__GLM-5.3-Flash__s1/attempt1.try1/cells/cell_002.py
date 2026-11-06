import fsspec, time, os
fs = fsspec.filesystem('onedata')
t0 = time.time()
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print('downloaded in %.1f s' % (time.time()-t0))
print(os.path.getsize('/work/sst_s2.nc'))