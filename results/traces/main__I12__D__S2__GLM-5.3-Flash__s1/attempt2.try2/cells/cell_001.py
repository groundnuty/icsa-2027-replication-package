import fsspec, os
fs = fsspec.filesystem('onedata')
os.makedirs('/work/s2z', exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/s2z/sst_s2.nc')
print(os.path.getsize('/work/s2z/sst_s2.nc'))