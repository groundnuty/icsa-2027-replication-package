import fsspec
fs = fsspec.filesystem('onedata')
# try downloading sst_s2.nc
fs.get('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
import os
print(os.path.getsize('/work/sst_s2.nc'))
