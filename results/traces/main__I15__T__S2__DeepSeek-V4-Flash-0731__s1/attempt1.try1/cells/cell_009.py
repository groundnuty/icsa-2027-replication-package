
import numpy as np
import pandas as pd

base_time = np.load('base_time.npy').astype('datetime64[D]').astype('datetime64[ns]')

# Check for leap year dates in baseline
from datetime import date

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return cum_days[month - 1] + day

base_dates = [pd.Timestamp(t).to_pydatetime() for t in base_time]

# Find Feb 29 dates
feb29 = [d for d in base_dates if d.month == 2 and d.day == 29]
print('Feb 29 dates in baseline:', feb29)

# Check what DOY values exist
base_doy = np.array([day_of_year(d) for d in base_dates])
print('Unique DOYs:', sorted(set(base_doy)))
print('Min:', base_doy.min(), 'Max:', base_doy.max())
print('Contains 60?', 60 in set(base_doy))
