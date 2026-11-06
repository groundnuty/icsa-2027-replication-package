
import numpy as np
import datetime

def doy_from_date(date):
    """Compute day of year 1-366 by month and day."""
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[date.month - 1] + date.day - 1

# Extended range: 1991-12-27 to 2003-01-05
ext_start = datetime.date(1991, 12, 27)
ext_end = datetime.date(2003, 1, 5)

# Baseline range: 1992-01-01 to 2002-12-31
base_start = datetime.date(1992, 1, 1)
base_end = datetime.date(2002, 12, 31)

# Generate all extended dates
ext_dates = []
d = ext_start
while d <= ext_end:
    ext_dates.append(d)
    d += datetime.timedelta(days=1)
print(f"Extended range: {ext_start} to {ext_end}, {len(ext_dates)} days")

# Generate all baseline dates
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += datetime.timedelta(days=1)
print(f"Baseline range: {base_start} to {base_end}, {len(base_dates)} days")

# For each date X in extended range, find baseline dates Y with |X-Y| <= 5
# For each such Y, X contributes to pool of doy(Y)
# We'll build: for each doy d, the list of X dates contributing to pool d
from collections import defaultdict
doy_to_dates = defaultdict(list)

for X in ext_dates:
    # Find baseline dates Y with |X-Y| <= 5
    for delta in range(-5, 6):
        Y = X + datetime.timedelta(days=delta)
        if base_start <= Y <= base_end:
            d = doy_from_date(Y)
            if d != 60:  # Day 60 gets no pool of its own
                doy_to_dates[d].append(X)

# Check pool sizes
pool_sizes = {d: len(dates) for d, dates in doy_to_dates.items()}
print(f"Number of doys with pools: {len(pool_sizes)}")
print(f"Pool size range: {min(pool_sizes.values())} to {max(pool_sizes.values())}")

# Show a few examples
for d in [1, 2, 59, 61, 153, 244, 365, 366]:
    print(f"doy {d}: {len(doy_to_dates[d])} dates")
    if len(doy_to_dates[d]) > 0:
        print(f"  First few: {doy_to_dates[d][:3]}")
        print(f"  Last few: {doy_to_dates[d][-3:]}")
