import fsspec
import os

fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
all_files = fs.ls(root)
basenames = [os.path.basename(f) for f in all_files]
# Filenames are sst_YYYYMMDD.nc
dates_str = [f[4:-3] for f in basenames if f.startswith('sst_') and f.endswith('.nc')]
dates_str.sort()

if dates_str:
    print(f"First date: {dates_str[0]}")
    print(f"Last date: {dates_str[-1]}")
    print(f"Total files: {len(dates_str)}")
else:
    print("No sst_YYYYMMDD.nc files found.")
