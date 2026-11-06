
import fsspec
fs = fsspec.filesystem('onedata')
print("Downloading...")
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
import os
print("Size:", os.path.getsize('/work/sst_s2.nc'))
