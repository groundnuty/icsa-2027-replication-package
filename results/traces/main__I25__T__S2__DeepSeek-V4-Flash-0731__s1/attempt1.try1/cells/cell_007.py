
import numpy as np
from datetime import datetime, timedelta

def day_of_year(dt):
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_leap[dt.month - 1] + dt.day

# Convert numpy datetime64 to datetime for the baseline period
# Let's test the day_of_year function on a range of dates

# For each day d (1-366, d != 60), the pool is all SST values whose date is within
# ±5 calendar days of a baseline date (1992-01-01 to 2002-12-31) whose day of year is d.

# Let's understand: for a given day d, we need to find all baseline dates y in [1992-01-01, 2002-12-31]
# such that doy(y) = d. Then for each such y, the pool includes dates from y-5 to y+5.
# The pool is the union of all these date ranges.

# Actually, I realize we need to be more careful. Let me re-read:
# "For each day of year d other than 60, the pool is every SST value whose date lies within ±5 calendar days 
# of a baseline date (1992-01-01 to 2002-12-31) whose day of year is d."

# So the pool for day d = { SST(x) : x is a date, ∃ baseline date y with doy(y)=d and |x-y| ≤ 5 days }

# This means we can precompute for each date x in our loaded data (1991-12-27 to 2003-01-05),
# which days d it belongs to the pool of.

# For each baseline date y in [1992-01-01, 2002-12-31]:
#   d = doy(y)
#   For each date x in [y-5, y+5]:
#     x belongs to pool of day d

# Let me build this mapping.

# First, get all baseline dates in [1992-01-01, 2002-12-31]
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Generate all baseline dates
all_baseline_dates = []
d = baseline_start
while d <= baseline_end:
    all_baseline_dates.append(d)
    d += timedelta(days=1)

# For each day d in 1-366 (except 60), find which loaded dates belong to its pool
# We need dates from 1991-12-27 to 2003-01-05

# Precompute: for each day d, which dates x (in our loaded range) are in the pool?
# We can do this by iterating over baseline dates and marking their windows.

# Let's think about this more efficiently.
# For each loaded date x, we need to check: does there exist a baseline date y such that
# doy(y) = d and |x - y| <= 5 days?

# For a given date x, which days d could it contribute to?
# For each baseline date y within 5 days of x, d = doy(y).
# So x contributes to all days d where doy(y) = d for some y in [x-5, x+5] ∩ [1992-01-01, 2002-12-31].

# This is getting complex. Let me just implement it directly.

# Approach: iterate over all baseline dates y, get doy(y) = d, and add all dates in [y-5, y+5] to pool d.

# But I need to do this per cell. The pools are per cell (each cell has its own pool).
# Let me structure this differently.

# Actually, I should think about what the pool for each day d contains.
# The pool for day d contains all SST values from dates in the union of [y-5, y+5] for all baseline y with doy(y)=d.

# Since I'm working with a specific region (60x60 cells), I need to load the baseline SST data 
# for those cells and process it.

# Let me plan the full implementation:
# 1. Load target data (2016-06-01 to 2016-08-31) for region
# 2. Load baseline data (1991-12-27 to 2003-01-05) for region
# 3. Identify sea cells (SST finite on every target day)
# 4. For each day d (1-366, d≠60), build the pool for each sea cell
# 5. Compute threshold (90th percentile) and climatology (mean) for each day d and sea cell
# 6. Set day 60 = mean of days 59 and 61
# 7. Smooth with 31-day centered moving mean that wraps
# 8. Find per-cell MHWs in target period
# 9. Aggregate to regional events

# Let me now write this code. I'll try to vectorize it as much as possible.

# First, let me compute the mapping from loaded date index to day-of-year pools.
# For the baseline period 1991-12-27 to 2003-01-05 (inclusive), I have 4028 dates.
# Let me compute for each loaded date, which day d's pool it belongs to.

# Actually, a cleaner approach: for each day d (1-366, d≠60), 
# find which loaded dates belong to its pool.

# Given baseline dates y with doy(y) = d, the pool for d includes dates in [y-5, y+5].
# These dates range from (earliest y - 5) to (latest y + 5).

# For day d, the baseline dates with doy(y)=d are all the dates with that month/day in each year 1992-2002.
# The windows around these dates cover a contiguous range of dates.

# Let me think about it differently. For a given day d (corresponding to a specific month/day):
# The pool dates are all dates x such that there exists a year y in 1992-2002 where
# |x - date(y, month, day)| <= 5 days.

# This means for each year y in 1992-2002:
#   dates in [date(y, m, d) - 5, date(y, m, d) + 5] are in the pool

# Since these windows are 11 days wide (y-5 to y+5) and repeated each year,
# the pool for day d covers approximately 11 years × 11 days = 121 dates.

# But wait, the windows from adjacent years can overlap. For example, if day d = 153 (June 1),
# then for year 1992: May 27 to Jun 6; for year 1993: May 27 to Jun 6, etc.
# These don't overlap because they're in different years.

# So for day d = 153 (June 1), the pool includes dates from:
# 1992-05-27 to 1992-06-06, 1993-05-27 to 1993-06-06, ..., 2002-05-27 to 2002-06-06
# That's 11 × 11 = 121 dates (approximately).

# Let me code this up properly.

print("Planning complete. Now implementing.")
