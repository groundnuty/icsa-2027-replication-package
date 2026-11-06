from datetime import date, timedelta
import numpy as np

def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

def date_to_doy(d):
    return month_day_to_doy(d.month, d.day)

# Baseline dates: 1992-01-01 to 2002-12-31
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# Build list of all baseline dates
all_baseline_dates = []
current = baseline_start
while current <= baseline_end:
    all_baseline_dates.append(current)
    current += timedelta(days=1)

print(f"Baseline dates: {len(all_baseline_dates)}")

# For each day-of-year d (1-366), find the baseline dates with that day-of-year
doy_to_baseline_dates = {}
for bd in all_baseline_dates:
    d = date_to_doy(bd)
    if d not in doy_to_baseline_dates:
        doy_to_baseline_dates[d] = []
    doy_to_baseline_dates[d].append(bd)

# Check: how many day-of-years are covered
print(f"Day-of-years with baseline dates: {len(doy_to_baseline_dates)}")
# Check day 60
print(f"Day 60 baseline dates: {doy_to_baseline_dates.get(60, [])}")

# For each day-of-year d, build the set of dates contributing to the pool
# Date D contributes to pool d if D is within ±5 days of some baseline date with day-of-year d
# But actually we need dates within ±5 days of baseline dates with day-of-year d

# All dates we have loaded: 1991-12-27 to 2003-01-05
all_loaded_dates = []
current = date(1991, 12, 27)
while current <= date(2003, 1, 5):
    all_loaded_dates.append(current)
    current += timedelta(days=1)

print(f"Loaded dates: {len(all_loaded_dates)}")

# Build a date->index mapping
date_to_idx = {d: i for i, d in enumerate(all_loaded_dates)}

# For each day-of-year d, collect the pool indices
doy_to_pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    if d not in doy_to_baseline_dates:
        doy_to_pool_indices[d] = []
        continue
    
    pool_dates = set()
    for bd in doy_to_baseline_dates[d]:
        for offset in range(-5, 6):
            pd = bd + timedelta(days=offset)
            pool_dates.add(pd)
    
    # Convert to indices in our loaded data
    idx = []
    for pd in pool_dates:
        if pd in date_to_idx:
            idx.append(date_to_idx[pd])
    
    doy_to_pool_indices[d] = sorted(idx)

# Check some day-of-years
print(f"\nDay 1 pool size: {len(doy_to_pool_indices[1])}")
print(f"Day 59 pool size: {len(doy_to_pool_indices[59])}")
print(f"Day 61 pool size: {len(doy_to_pool_indices[61])}")
print(f"Day 153 pool size: {len(doy_to_pool_indices[153])}")
print(f"Day 366 pool size: {len(doy_to_pool_indices[366])}")
print(f"Day 365 pool size: {len(doy_to_pool_indices[365])}")

# Check which dates are in day 1's pool
for idx in doy_to_pool_indices[1]:
    print(f"  {all_loaded_dates[idx]}")
