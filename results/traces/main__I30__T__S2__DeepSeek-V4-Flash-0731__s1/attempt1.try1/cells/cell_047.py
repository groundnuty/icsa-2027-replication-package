
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Load data
baseline_time = np.load('/tmp/baseline_time.npy')

def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
base_doy = np.array([doy_from_date(d) for d in baseline_dates])

strict_base_start = pd.Timestamp('1992-01-01')
strict_base_end = pd.Timestamp('2002-12-31')
strict_idx = np.where([(d >= strict_base_start and d <= strict_base_end) for d in baseline_dates])[0]

base_date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

# Find Feb 29 dates in the baseline
feb29_indices = []
for i, d in enumerate(baseline_dates):
    if d.month == 2 and d.day == 29:
        feb29_indices.append(i)

print("Feb 29 dates in baseline:")
for i in feb29_indices:
    print(f"  {baseline_dates[i].strftime('%Y-%m-%d')} (DOY {base_doy[i]})")

# Check which pools include Feb 29 values
# For DOY 58 (Feb 27), the pool includes dates within ±5 days of Feb 27 (1992-2002)
# Feb 29 would be within ±5 of Feb 27 if the year is a leap year
for d in [57, 58, 59, 60, 61, 62, 63]:
    if d == 60:
        continue
    
    dates_with_doy = []
    for i in strict_idx:
        if base_doy[i] == d:
            dates_with_doy.append(baseline_dates[i])
    
    pool_indices = set()
    for bd in dates_with_doy:
        for offset in range(-5, 6):
            candidate = bd + timedelta(days=offset)
            if candidate in base_date_to_idx:
                pool_indices.add(base_date_to_idx[candidate])
    
    # Check if any Feb 29 is in this pool
    feb29_in_pool = [baseline_dates[i].strftime('%Y-%m-%d') for i in pool_indices 
                     if baseline_dates[i].month == 2 and baseline_dates[i].day == 29]
    if feb29_in_pool:
        print(f"DOY {d}: Feb 29 in pool: {feb29_in_pool}")
    else:
        print(f"DOY {d}: No Feb 29 in pool")
