import os
import re

dir_path = '/data/icsa2027_data_20261101T090944Z/s1z'
files = os.listdir(dir_path)
sst_files = [f for f in files if f.startswith('sst_') and f.endswith('.nc')]

# Extract dates from filenames
dates = []
for f in sst_files:
    match = re.search(r'sst_(\d{8})\.nc', f)
    if match:
        dates.append(match.group(1))

dates.sort()
if dates:
    print(f"Number of files: {len(dates)}")
    print(f"First date: {dates[0]}")
    print(f"Last date: {dates[-1]}")
else:
    print("No matching files found.")
