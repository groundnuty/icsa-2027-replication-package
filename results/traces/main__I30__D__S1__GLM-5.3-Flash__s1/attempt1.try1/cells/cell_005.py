import fsspec, os, time
fs = fsspec.filesystem('onedata')
t0=time.time()
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print('downloaded in', time.time()-t0, 's; size MB:', os.path.getsize('/work/sst_s2.nc')/1e6)
