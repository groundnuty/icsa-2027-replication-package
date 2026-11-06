import fsspec
import os

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(path)
sst_files = sorted([f for f in files if os.path.basename(f).startswith('sst_') and os.path.basename(f).endswith('.nc')])

if sst_files:
    print(f"First file: {sst_files[0]}")
    print(f"Last file: {sst_files[-1]}")
    print(f"Total SST files: {len(sst_files)}")
else:
    print("No SST files found in s1z.")
