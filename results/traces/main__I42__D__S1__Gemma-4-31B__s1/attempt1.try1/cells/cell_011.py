import fsspec
import os

fs = fsspec.filesystem('onedata')
remote_file = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_file = '/work/sst_s2.nc'

print("Downloading sst_s2.nc... this may take a while.")
try:
    fs.get(remote_file, local_file)
    print("Download complete.")
except Exception as e:
    print(f"Download failed: {e}")
