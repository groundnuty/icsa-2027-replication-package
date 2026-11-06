
import numpy as np
import datetime

# Load baseline dates
base_dates = np.load('base_dates.npy')
base_dates = [datetime.date.fromordinal(int(x)) for x in base_dates]

# Define doy function
def date_to_doy(d):
    """Map date to day of year 1-366 using the task's mapping."""
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = d.day
    for m in range(1, d.month):
        doy += days_in_month[m-1]
    return doy

# Identify baseline dates in 1992-2002
baseline_years = list(range(1992, 2003))
baseline_dates = [d for d in base_dates if 1992 <= d.year <= 2002]
print(f"Baseline dates in 1992-2002: {len(baseline_dates)}")

# Group by doy
from collections import defaultdict
dates_by_doy = defaultdict(list)
for d in baseline_dates:
    doy = date_to_doy(d)
    dates_by_doy[doy].append(d)

print(f"Doys with baseline dates: {len(dates_by_doy)}")
# Check a few
for doy in [1, 59, 60, 61, 365, 366]:
    print(f"  doy={doy}: {[str(d) for d in dates_by_doy.get(doy, [])]}")
