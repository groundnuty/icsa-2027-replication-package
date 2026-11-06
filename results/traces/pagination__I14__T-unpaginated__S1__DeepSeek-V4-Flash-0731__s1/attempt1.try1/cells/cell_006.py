
import fsspec
import numpy as np
from datetime import date, timedelta

fs = fsspec.filesystem('onedata')

# Get list of files we need
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

# Target period files
target_dates = []
d = date(2015, 6, 1)
while d <= date(2015, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)
print(f"Target days: {len(target_dates)}")
print(f"First: {target_dates[0]}, Last: {target_dates[-1]}")

# Baseline dates: 1992-01-01 to 2002-12-31, plus windows
# For day-of-year d, the pool includes dates within ±5 calendar days of baseline dates whose day-of-year is d
# But the windows reach 5 days beyond the baseline ends (1991-12-27 to 2003-01-05)
# So we need all dates from 1991-12-27 to 2003-01-05

baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)
print(f"Baseline+window days: {len(baseline_dates)}")
print(f"First: {baseline_dates[0]}, Last: {baseline_dates[-1]}")

# Check that all files exist
# For target
for td in target_dates:
    fname = f"sst_{td.strftime('%Y%m%d')}.nc"
    if not fs.exists(f"{base_dir}/{fname}"):
        print(f"MISSING: {fname}")

# For baseline
missing_count = 0
for bd in baseline_dates:
    fname = f"sst_{bd.strftime('%Y%m%d')}.nc"
    if not fs.exists(f"{base_dir}/{fname}"):
        print(f"MISSING baseline: {fname}")
        missing_count += 1
print(f"Missing baseline files: {missing_count}")
