import fsspec
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
all_files = fs.ls(path)

# Convert file list to a set of dates
dates = []
for f in all_files:
    fname = os.path.basename(f)
    if fname.startswith('sst_') and fname.endswith('.nc'):
        try:
            date_str = fname[4:12]
            dates.append(pd.to_datetime(date_str, format='%Y%m%d'))
        except:
            pass

dates = sorted(dates)
if dates:
    print(f"Date range: {dates[0].date()} to {dates[-1].date()}")
    print(f"Total files: {len(dates)}")
else:
    print("No SST files found.")

# Check baseline and target availability
baseline_start = pd.Timestamp('1991-12-27')
baseline_end = pd.Timestamp('2003-01-05')
target_start = pd.Timestamp('2008-06-01')
target_end = pd.Timestamp('2008-08-31')

baseline_available = [d for d in dates if baseline_start <= d <= baseline_end]
target_available = [d for d in dates if target_start <= d <= target_end]

print(f"Baseline available: {len(baseline_available)} / { (baseline_end - baseline_start).days + 1 }")
print(f"Target available: {len(target_available)} / { (target_end - target_start).days + 1 }")

if len(baseline_available) < (baseline_end - baseline_start).days + 1:
    # Find gaps in baseline
    all_baseline_dates = pd.date_range(baseline_start, baseline_end)
    missing_baseline = set(all_baseline_dates) - set(baseline_available)
    print(f"Missing baseline dates: {len(missing_baseline)}")

if len(target_available) < (target_end - target_start).days + 1:
    # Find gaps in target
    all_target_dates = pd.date_range(target_start, target_end)
    missing_target = set(all_target_dates) - set(target_available)
    print(f"Missing target dates: {len(missing_target)}")
