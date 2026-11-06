
import numpy as np
import datetime

def day_of_year(dt):
    """Map date to day of year 1-366."""
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Test with baseline dates
print(f"31 Dec 1991: doy={day_of_year(datetime.date(1991,12,31))}")
print(f"1 Jan 1992: doy={day_of_year(datetime.date(1992,1,1))}")
print(f"28 Feb 1992: doy={day_of_year(datetime.date(1992,2,28))}")
print(f"29 Feb 1992: doy={day_of_year(datetime.date(1992,2,29))}")
print(f"1 Mar 1992: doy={day_of_year(datetime.date(1992,3,1))}")
print(f"5 Jan 2003: doy={day_of_year(datetime.date(2003,1,5))}")

# For the baseline, I need to find which dates in 1992-2002 have each day-of-year
# and then include ±5 days around them

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')
target_sst = np.load('/tmp/target_sst.npy')
baseline_times = np.load('/tmp/baseline_times.npy')
target_times = np.load('/tmp/target_times.npy')

baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

# Build a date->index mapping for baseline
baseline_date_to_idx = {}
for i, d in enumerate(baseline_dates):
    baseline_date_to_idx[d] = i

# Identify sea cells (finite on all target days)
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))
print(f"Sea cells: {sea_mask.sum()}")

# For each day-of-year d (except 60), construct the pool
# The pool for doy d is: all SST values whose date is within ±5 days of a baseline date (1992-2002) with doy d

# First, build a list of "baseline reference dates" for each doy
# Baseline reference period: 1992-01-01 to 2002-12-31
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

# For each doy, find all dates in the baseline period with that doy
# Then for each such date, find all dates within ±5 days

# Let's build a map from date to index in baseline data
# All dates are already in the baseline data (1991-12-27 to 2003-01-05)

# For efficiency, let me precompute the date-to-index mapping
# Then for each doy, find all contributing dates

# For each doy d (except 60), the pool dates are:
#   For each D in [1992-01-01, 2002-12-31] with doy(D)=d:
#     Include all dates D' with |D' - D| <= 5 days

# These pool dates are all within [1992-01-01 - 5, 2002-12-31 + 5] = [1991-12-27, 2003-01-05]
# which is exactly our baseline data range

# So I can build for each doy d the list of indices into baseline data

# Find all baseline dates with each doy in the reference period 1992-2002
from collections import defaultdict
doy_dates = defaultdict(list)
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    doy_dates[doy].append(d)
    d += datetime.timedelta(days=1)

# Now for each doy, find all pool indices
# For each date D with doy(D)=d, include dates D-5 to D+5
doy_pool_indices = {}
for doy, dates in doy_dates.items():
    if doy == 60:
        continue  # Day 60 gets no pool of its own
    pool_dates = set()
    for D in dates:
        for offset in range(-5, 6):
            pool_dates.add(D + datetime.timedelta(days=offset))
    # Convert to indices
    indices = []
    for pd in sorted(pool_dates):
        if pd in baseline_date_to_idx:
            indices.append(baseline_date_to_idx[pd])
    doy_pool_indices[doy] = indices

# Check pool sizes for a few days
for doy in [1, 59, 61, 153, 182, 366]:
    print(f"doy {doy}: {len(doy_pool_indices[doy])} dates in pool")
