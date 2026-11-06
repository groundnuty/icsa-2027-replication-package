import fsspec
import os

fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
all_files = fs.find(root)
cmems_files = [f for f in all_files if 'cmems' in f.lower()]
print(f"Found {len(cmems_files)} files containing 'cmems'.")
if cmems_files:
    print(cmems_files[:10])
