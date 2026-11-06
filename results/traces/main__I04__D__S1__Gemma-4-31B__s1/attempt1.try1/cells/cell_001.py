import fsspec
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base_path)
print(f"Found {len(files)} files in {base_path}")
# Look for SST files
sst_files = [f for f in files if 'sst' in f and 'temp' in f]
print(f"Found {len(sst_files)} SST files")
for f in sst_files[:10]:
    print(f)
