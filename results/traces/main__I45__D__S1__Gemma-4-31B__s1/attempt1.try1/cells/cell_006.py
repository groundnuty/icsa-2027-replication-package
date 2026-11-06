import fsspec
import re

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s2z'
files = fs.ls(remote_dir)

dates = []
for f in files:
    match = re.search(r'sst_(\d{8})\.nc', f)
    if match:
        dates.append(match.group(1))

sorted_dates = sorted(dates)
if sorted_dates:
    print(f"Earliest date in s2z: {sorted_dates[0]}")
    print(f"Latest date in s2z: {sorted_dates[-1]}")
    print(f"Total files in s2z: {len(sorted_dates)}")
else:
    print("No matching files found in s2z.")
