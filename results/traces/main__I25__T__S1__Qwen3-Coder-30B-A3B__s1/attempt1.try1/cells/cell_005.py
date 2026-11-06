import fsspec
import re
from datetime import datetime

fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')

# Extract dates from filenames
date_pattern = re.compile(r'sst_(\d{8})\.nc')
dates = []

for f in files:
    match = date_pattern.search(f)
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            dates.append((date_obj, f))
        except ValueError:
            continue

# Sort by date
dates.sort()

print(f"Available date range: {dates[0][0].strftime('%Y-%m-%d')} to {dates[-1][0].strftime('%Y-%m-%d')}")
print(f"Total files: {len(dates)}")
print("First 10 files:")
for i in range(min(10, len(dates))):
    print(f"  {dates[i][0].strftime('%Y-%m-%d')}: {dates[i][1]}")