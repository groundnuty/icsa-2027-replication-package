import fsspec
import re

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(remote_dir)

# Extract dates from filenames like 'sst_YYYYMMDD.nc'
dates = []
for f in files:
    match = re.search(r'sst_(\d{8})\.nc', f)
    if match:
        dates.append(match.group(1))

sorted_dates = sorted(dates)
print(f"Earliest date: {sorted_dates[0]}")
print(f"Latest date: {sorted_dates[-1]}")
print(f"Total files: {len(sorted_dates)}")
