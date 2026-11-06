import fsspec, os
fs = fsspec.filesystem('onedata')
os.makedirs('/work', exist_ok=True)
os.makedirs('/work/output', exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print(os.path.getsize('/work/sst_s2.nc'))