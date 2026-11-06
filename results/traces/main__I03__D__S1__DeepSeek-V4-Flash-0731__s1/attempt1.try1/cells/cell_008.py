
import fsspec
fs = fsspec.filesystem('onedata')
# Download the s2z file
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print("Downloaded")
import os
print(f"File size: {os.path.getsize('/work/sst_s2.nc')}")
