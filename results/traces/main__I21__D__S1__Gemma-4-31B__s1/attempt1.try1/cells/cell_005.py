import fsspec
import re

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s2z'
files = fs.ls(remote_dir)

# Filter files that match the sst_YYYYMMDD.nc pattern
sst_files_s2z = [f for f in files if re.match(r'.*/sst_\d{8}\.nc$', f)]
sst_files_s2z.sort()

print(f"Total SST files in s2z: {len(sst_files_s2z)}")
print(f"First file in s2z: {sst_files_s2z[0]}")
print(f"Last file in s2z: {sst_files_s2z[-1]}")
