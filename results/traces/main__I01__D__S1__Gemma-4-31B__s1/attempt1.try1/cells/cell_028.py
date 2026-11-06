import fsspec
import os

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
all_files = fs.ls(path)
all_files.sort()
print(f"Total files in {path}: {len(all_files)}")
print("First 10 files:")
for f in all_files[:10]:
    print(f)
print("Last 10 files:")
for f in all_files[-10:]:
    print(f)
