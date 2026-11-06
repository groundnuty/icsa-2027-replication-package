import os
import re
from datetime import datetime

# Check what date files exist in the directory
date_pattern = re.compile(r'sst_(\d{8})\.nc')
dates = []

for filename in os.listdir("/data/icsa2027_data_20261101T090944Z/s1z"):
    match = date_pattern.match(filename)
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            dates.append(date_obj)
        except ValueError:
            continue

dates.sort()
print(f"Date range in dataset: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
print(f"Total files: {len(dates)}")

# Check if we have the required period
target_start = datetime(2004, 6, 1)
target_end = datetime(2004, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

print(f"\nTarget period: {target_start.strftime('%Y-%m-%d')} to {target_end.strftime('%Y-%m-%d')}")
print(f"Baseline period: {baseline_start.strftime('%Y-%m-%d')} to {baseline_end.strftime('%Y-%m-%d')}")

# Check if our required dates are available
has_target_period = all(target_start <= date <= target_end for date in dates)
has_baseline_period = all(baseline_start <= date <= baseline_end for date in dates)

print(f"Has complete target period: {has_target_period}")
print(f"Has complete baseline period: {has_baseline_period}")