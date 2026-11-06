
import numpy as np
from datetime import date, timedelta

# Define DOY mapping
def doy_from_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month - 1] + d.day

# Baseline dates: 1992-01-01 to 2002-12-31
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# Build dictionary: doy -> list of baseline dates with that doy
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)

doy_to_baseline_dates = {}
for d in baseline_dates:
    doy = doy_from_date(d)
    if doy not in doy_to_baseline_dates:
        doy_to_baseline_dates[doy] = []
    doy_to_baseline_dates[doy].append(d)

# Check how many baseline dates per doy
print(f"Total DOYs: {len(doy_to_baseline_dates)}")
for doy in [1, 59, 60, 61, 366]:
    dates = doy_to_baseline_dates.get(doy, [])
    print(f"DOY {doy}: {len(dates)} baseline dates, e.g., {dates[0]} to {dates[-1]}")
