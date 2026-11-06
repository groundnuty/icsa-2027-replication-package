
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

# Load saved data
base_data = np.load('/tmp/base_data.npy')
tgt_data = np.load('/tmp/tgt_data.npy')
base_times = np.load('/tmp/base_times.npy')
tgt_times = np.load('/tmp/tgt_times.npy')
lats = np.load('/tmp/lats.npy')
lons = np.load('/tmp/lons.npy')

def day_of_year(month, day):
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and day == 29:
        return 60
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:
        doy += 1
    return doy

def date_to_doy(dt):
    # dt is a numpy datetime64
    dt_py = pd.Timestamp(dt).to_pydatetime()
    return day_of_year(dt_py.month, dt_py.day)

import pandas as pd

# Convert base times to Python datetimes
base_dt = [pd.Timestamp(t).to_pydatetime() for t in base_times]
tgt_dt = [pd.Timestamp(t).to_pydatetime() for t in tgt_times]

print("First base date:", base_dt[0])
print("Last base date:", base_dt[-1])
print("First target date:", tgt_dt[0])
print("Last target date:", tgt_dt[-1])

# Compute day-of-year for each base date
base_doy = np.array([date_to_doy(t) for t in base_dt])
print("Base DOY range:", base_doy.min(), base_doy.max())
print("Base DOY unique count:", len(np.unique(base_doy)))

# Compute day-of-year for each target date
tgt_doy = np.array([date_to_doy(t) for t in tgt_dt])
print("Target DOY range:", tgt_doy.min(), tgt_doy.max())
print("Target DOY values:", tgt_doy)
