
import pandas as pd
import numpy as np

# All dates in the dataset
all_dates = pd.date_range('1982-01-01', '2023-12-31', freq='D')

# Extended baseline range
ext_start = pd.Timestamp('1991-12-27')
ext_end = pd.Timestamp('2003-01-05')
ext_dates = all_dates[(all_dates >= ext_start) & (all_dates <= ext_end)]
print(f"Extended baseline: {ext_dates[0]} to {ext_dates[-1]}, count: {len(ext_dates)}")

# Baseline range (the actual baseline years)
base_start = pd.Timestamp('1992-01-01')
base_end = pd.Timestamp('2002-12-31')
base_dates = all_dates[(all_dates >= base_start) & (all_dates <= base_end)]
print(f"Baseline: {base_dates[0]} to {base_dates[-1]}, count: {len(base_dates)}")

# Day of year function
def fixed_doy(date):
    cum = [0, 31, 31+29, 31+29+31, 31+29+31+30, 31+29+31+30+31,
           31+29+31+30+31+30, 31+29+31+30+31+30+31,
           31+29+31+30+31+30+31+31, 31+29+31+30+31+30+31+31+30,
           31+29+31+30+31+30+31+31+30+31,
           31+29+31+30+31+30+31+31+30+31+30]
    return cum[date.month-1] + date.day

# Compute doy for all baseline dates
base_doy = np.array([fixed_doy(d) for d in base_dates])

# For each day d (1-366, d!=60), find the window dates
window_dates_by_doy = {}
for d in range(1, 367):
    if d == 60:
        continue
    # Find all baseline dates with this doy
    b_dates = base_dates[base_doy == d]
    # For each baseline date, expand to ±5 days
    window = set()
    for b in b_dates:
        for dt in pd.date_range(b - pd.Timedelta(days=5), b + pd.Timedelta(days=5), freq='D'):
            window.add(dt)
    window_dates_by_doy[d] = sorted(window)

# Check sizes
for d in [1, 2, 59, 61, 365, 366]:
    print(f"Day {d}: {len(window_dates_by_doy[d])} dates in pool")
