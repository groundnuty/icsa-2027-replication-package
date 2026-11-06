
# Check what files we need and plan
import os
from datetime import date, timedelta

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# List all files
all_files = sorted(os.listdir(data_dir))
print(f"Total files: {len(all_files)}")

# Build set of dates we need for baseline pools
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

doy_to_baseline_dates = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy not in doy_to_baseline_dates:
        doy_to_baseline_dates[doy] = []
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for b in doy_to_baseline_dates.get(doy, []):
        for i in range(-5, 6):
            pool_dates.add(b + timedelta(days=i))
    doy_to_pool_dates[doy] = pool_dates

all_pool_dates = set()
for dates in doy_to_pool_dates.values():
    all_pool_dates.update(dates)
print(f"Unique pool dates: {len(all_pool_dates)}")

# Target dates
target_start = date(2003, 6, 1)
target_end = date(2003, 8, 31)

target_dates = set()
d = target_start
while d <= target_end:
    target_dates.add(d)
    d += timedelta(days=1)
print(f"Target dates: {len(target_dates)}")

# Check that all needed files exist
all_needed = all_pool_dates | target_dates
needed_strs = set()
for dt in all_needed:
    needed_strs.add(f'sst_{dt.strftime("%Y%m%d")}.nc')

missing = needed_strs - set(all_files)
print(f"Missing files: {len(missing)}")
if missing:
    print(sorted(missing)[:5])
