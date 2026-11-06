
import os

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
files = sorted(os.listdir(data_dir))
print(f"Number of files: {len(files)}")
print(f"First 5: {files[:5]}")
print(f"Last 5: {files[-5:]}")

# Extract dates from filenames
import re
dates = []
for f in files:
    m = re.match(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))

dates.sort()
print(f"\nFirst date: {dates[0]}")
print(f"Last date: {dates[-1]}")
print(f"Total dates: {len(dates)}")

# Check if we have all dates between
from datetime import datetime, timedelta
start = datetime.strptime(dates[0], '%Y%m%d')
end = datetime.strptime(dates[-1], '%Y%m%d')
expected = (end - start).days + 1
print(f"Expected dates: {expected}, found: {len(dates)}")

# Check for specific dates we need
# Baseline: 1991-12-27 to 2003-01-05 (with buffer)
# Target: 2014-06-01 to 2014-08-31
needed_start = datetime(1991, 12, 27)
needed_end = datetime(2003, 1, 5)
target_start = datetime(2014, 6, 1)
target_end = datetime(2014, 8, 31)

all_dates_set = set(dates)

# Check baseline dates
missing_baseline = []
d = needed_start
while d <= needed_end:
    ds = d.strftime('%Y%m%d')
    if ds not in all_dates_set:
        missing_baseline.append(ds)
    d += timedelta(days=1)
print(f"Missing baseline dates: {missing_baseline[:20]}... (total {len(missing_baseline)})")

# Check target dates
missing_target = []
d = target_start
while d <= target_end:
    ds = d.strftime('%Y%m%d')
    if ds not in all_dates_set:
        missing_target.append(ds)
    d += timedelta(days=1)
print(f"Missing target dates: {missing_target}")

# Check which years are in the dataset
years = set()
for ds in dates:
    years.add(ds[:4])
print(f"\nYears in dataset: {sorted(years)}")
