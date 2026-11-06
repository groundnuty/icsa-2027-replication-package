import re
from datetime import datetime

# Get all filenames and extract dates
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
date_pattern = r'sst_(\d{8})\.nc'

dates = []
for f in files:
    match = re.search(date_pattern, f)
    if match:
        dates.append(datetime.strptime(match.group(1), '%Y%m%d'))

print(f"Date range: {min(dates)} to {max(dates)}")
print(f"Total files: {len(dates)}")

# Check a few sample dates
sample_dates = sorted(dates)[:10]
print("Sample dates:", [d.strftime('%Y-%m-%d') for d in sample_dates])