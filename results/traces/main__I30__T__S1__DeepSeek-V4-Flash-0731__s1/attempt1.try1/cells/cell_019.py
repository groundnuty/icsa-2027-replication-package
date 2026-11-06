
import numpy as np
import pandas as pd

baseline_data = np.load('/tmp/baseline_data.npy').astype(np.float64)
baseline_times = np.load('/tmp/baseline_times.npy').astype('datetime64[D]')

# Create a mapping from date -> index
time_index_map = {}
for i, t in enumerate(baseline_times):
    time_index_map[t] = i

print("Number of baseline time entries:", len(time_index_map))

# Define baseline period dates (1992-01-01 to 2002-12-31)
base_start = np.datetime64('1992-01-01', 'D')
base_end = np.datetime64('2002-12-31', 'D')

# Day of year function
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

def doy_from_dt64(t):
    dt = pd.Timestamp(t)
    return day_of_year(dt.month, dt.day)

# For each day of year, collect pool time indices
# Baseline dates are all dates from 1992-01-01 to 2002-12-31
# For each day of year d, find all baseline dates with that doy
# For each such date, add indices [b-5, b+5] to the pool

pool_indices = {}  # day_of_year -> list of time indices into baseline_data

for d in range(1, 367):
    if d == 60:
        continue
    indices = set()
    # Find all dates in baseline with doy = d
    # Iterate through years 1992-2002
    year = 1992
    while year <= 2002:
        # Find the date in this year with doy = d
        # Convert doy back to month/day
        # month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        remaining = d
        month = 0
        while remaining > month_days[month]:
            remaining -= month_days[month]
            month += 1
        day = remaining
        month += 1
        
        # Check if this date is valid (e.g., Feb 29 in non-leap year)
        is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
        if month == 2 and day == 29 and not is_leap:
            # Non-leap year doesn't have Feb 29 (day 60)
            # But for other days, the date should be valid
            year += 1
            continue
        
        # Create the baseline date
        b_date = np.datetime64(f'{year}-{month:02d}-{day:02d}', 'D')
        
        # Add indices for [b-5, b+5]
        for offset in range(-5, 6):
            date_i = b_date + np.timedelta64(offset, 'D')
            if date_i in time_index_map:
                indices.add(time_index_map[date_i])
        
        year += 1
    
    pool_indices[d] = sorted(indices)

print("Pool sizes for some days:")
for d in [1, 59, 61, 100, 150, 200, 250, 300, 366]:
    if d in pool_indices:
        print(f"  day {d}: {len(pool_indices[d])} indices")
    else:
        print(f"  day {d}: (no pool)")

# Check day 60 has no pool
print(f"day 60 in pool_indices: {60 in pool_indices}")
