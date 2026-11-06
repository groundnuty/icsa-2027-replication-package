import fsspec
import re

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(remote_dir)

# Filter files that match the sst_YYYYMMDD.nc pattern
sst_files = [f for f in files if re.match(r'.*/sst_\d{8}\.nc$', f)]
sst_files.sort()

print(f"Total SST files: {len(sst_files)}")
print(f"First file: {sst_files[0]}")
print(f"Last file: {sst_files[-1]}")
