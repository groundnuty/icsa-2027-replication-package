
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

# Check DOY 1 (Jan 1)
for d in [1, 59, 60, 61, 366]:
    if d == 60:
        print(f"\nDOY {d}: (no pool, skipped)")
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
    
    pool_indices = sorted(pool_indices)
    print(f"\nDOY {d}: {len(dates_with_doy)} baseline dates, pool size = {len(pool_indices)}")
    print(f"  First pool date: {baseline_dates[pool_indices[0]].strftime('%Y-%m-%d')}")
    print(f"  Last pool date: {baseline_dates[pool_indices[-1]].strftime('%Y-%m-%d')}")
    
    # Check if extension dates are included
    for i in pool_indices:
        date = baseline_dates[i]
        if date.year == 1991 or date.year == 2003:
            print(f"  Extension date in pool: {date.strftime('%Y-%m-%d')}")
