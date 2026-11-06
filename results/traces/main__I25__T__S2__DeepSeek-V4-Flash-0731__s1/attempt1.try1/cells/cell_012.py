
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

def day_of_year(dt):
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_leap[dt.month - 1] + dt.day

# Build mapping from each day d (1-366, d≠60) to the indices of loaded baseline dates
# that belong to its pool.

# I need to know which indices in my loaded baseline array (4028 dates from 1991-12-27 to 2003-01-05)
# correspond to each day d's pool.

# For each baseline date y (in [1992-01-01, 2002-12-31]) with doy(y)=d,
# the pool for d includes dates [y-5, y+5].
# These dates are in the range [1991-12-27, 2003-01-05].

# First, let me create an array of all baseline dates in my loaded data
# The loaded baseline data starts at 1991-12-27 and goes to 2003-01-05

# The baseline data I loaded has 4028 dates
# Let me verify this covers all days from 1991-12-27 to 2003-01-05

start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
num_days = (end - start).days + 1
print(f"Expected number of days: {num_days}")

# All dates in the loaded range
all_loaded_dates = []
d = start
while d <= end:
    all_loaded_dates.append(d)
    d += timedelta(days=1)
print(f"Actual loaded dates: {len(all_loaded_dates)}")
