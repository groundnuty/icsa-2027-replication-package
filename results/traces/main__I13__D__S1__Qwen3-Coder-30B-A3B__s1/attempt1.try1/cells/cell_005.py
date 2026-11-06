import fsspec
import os
from datetime import datetime

# Let's see how many years of data we have
fs = fsspec.filesystem('onedata')
base_path = '/icsa2027_data_20261101T090944Z/s1z'

# Get all files and sort them by date
files = []
for file in fs.ls(base_path):
    filename = os.path.basename(file)
    if filename.startswith('sst_') and len(filename) >= 13:
        date_str = filename[4:12]  # Extract YYYYMMDD part
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            files.append((date_obj, file))
        except ValueError:
            continue

files.sort()

print(f"Total files: {len(files)}")
print("First few files:")
for i in range(min(5, len(files))):
    print(f"  {files[i][0]} -> {os.path.basename(files[i][1])}")

print("Last few files:")
for i in range(max(0, len(files)-5), len(files)):
    print(f"  {files[i][0]} -> {os.path.basename(files[i][1])}")

# Check if we have sufficient data for baseline (1992-2002) and target (2021-06-01 to 2021-08-31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
target_start = datetime(2021, 6, 1)
target_end = datetime(2021, 8, 31)

has_baseline = any(baseline_start <= date <= baseline_end for date, _ in files)
has_target = any(target_start <= date <= target_end for date, _ in files)

print(f"\nBaseline period (1992-2002): {'Available' if has_baseline else 'Not available'}")
print(f"Target period (2021-06-01 to 2021-08-31): {'Available' if has_target else 'Not available'}")