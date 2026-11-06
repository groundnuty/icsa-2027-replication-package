
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')
baseline_time = np.load('/tmp/baseline_time.npy')

def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
base_doy = np.array([doy_from_date(d) for d in baseline_dates])

# Strict baseline dates
strict_base_start = pd.Timestamp('1992-01-01')
strict_base_end = pd.Timestamp('2002-12-31')
strict_idx = np.where([(d >= strict_base_start and d <= strict_base_end) for d in baseline_dates])[0]

# Build pool for DOY 153 (June 1) as an example
d = 153
dates_with_doy = []
for i in strict_idx:
    if base_doy[i] == d:
        dates_with_doy.append(baseline_dates[i])

print(f"Strict baseline dates with DOY {d}: {len(dates_with_doy)}")
for dt in dates_with_doy:
    print(f"  {dt.date()}")

# Build pool indices
base_date_to_idx = {d: i for i, d in enumerate(baseline_dates)}
pool_indices = set()
for bd in dates_with_doy:
    for offset in range(-5, 6):
        candidate = bd + timedelta(days=offset)
        if candidate in base_date_to_idx:
            pool_indices.add(base_date_to_idx[candidate])

pool_indices = sorted(pool_indices)
print(f"Pool size: {len(pool_indices)} dates")
print(f"First few pool dates: {[baseline_dates[i].strftime('%Y-%m-%d') for i in pool_indices[:15]]}")
print(f"Last few pool dates: {[baseline_dates[i].strftime('%Y-%m-%d') for i in pool_indices[-15:]]}")

# Check a specific pool date
for i in pool_indices:
    bd = baseline_dates[i]
    # Verify this date is within ±5 days of a strict baseline date with DOY 153
    in_pool = False
    for j in strict_idx:
        if base_doy[j] == 153:
            bd_j = baseline_dates[j]
            if abs((bd - bd_j).days) <= 5:
                in_pool = True
                break
    if not in_pool:
        print(f"ERROR: {bd.date()} should not be in pool for DOY 153")
    # Also check no dates are missing
