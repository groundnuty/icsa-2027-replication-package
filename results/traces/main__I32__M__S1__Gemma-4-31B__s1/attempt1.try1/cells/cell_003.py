import os
from datetime import datetime, timedelta

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
all_files = os.listdir(data_dir)

# Check for baseline years 1992-2002
# The windows extend to 1991-12-27 and 2003-01-05.
start_date = datetime(1991, 12, 27)
end_date = datetime(2003, 1, 5)
target_start = datetime(2005, 6, 1)
target_end = datetime(2005, 8, 31)

missing_baseline = []
curr = start_date
while curr <= end_date:
    filename = f"sst_{curr.strftime('%Y%m%d')}.nc"
    if filename not in all_files:
        missing_baseline.append(curr.strftime('%Y-%m-%d'))
    curr += timedelta(days=1)

missing_target = []
curr = target_start
while curr <= target_end:
    filename = f"sst_{curr.strftime('%Y%m%d')}.nc"
    if filename not in all_files:
        missing_target.append(curr.strftime('%Y-%m-%d'))
    curr += timedelta(days=1)

print(f"Missing baseline: {len(missing_baseline)}")
if missing_baseline:
    print(f"First 5 missing baseline: {missing_baseline[:5]}")
print(f"Missing target: {len(missing_target)}")
if missing_target:
    print(f"First 5 missing target: {missing_target[:5]}")
