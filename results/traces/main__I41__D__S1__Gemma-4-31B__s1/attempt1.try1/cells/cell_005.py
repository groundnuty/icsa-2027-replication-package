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

dates.sort()
if dates:
    print(f"Earliest date: {dates[0]}")
    print(f"Latest date: {dates[-1]}")
    print(f"Number of files: {len(dates)}")
else:
    print("No SST files found in s2z")
