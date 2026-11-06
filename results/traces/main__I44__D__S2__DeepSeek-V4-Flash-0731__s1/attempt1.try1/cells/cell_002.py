
import fsspec
import os

fs = fsspec.filesystem('onedata')
os.makedirs('/work', exist_ok=True)
print("Downloading...")
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print("Downloaded")
