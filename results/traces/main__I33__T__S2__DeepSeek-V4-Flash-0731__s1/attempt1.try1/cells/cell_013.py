
import numpy as np
import xarray as xr
from datetime import date, timedelta

# Load saved data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

# Day of year mapping
cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

# Baseline period: 1992-01-01 to 2002-12-31
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# All dates in the baseline dataset (1991-12-27 to 2003-01-05)
all_dates = baseline_data.time.values.astype('datetime64[D]').astype(object)

# Convert all dates to date objects
all_date_objs = [pd.Timestamp(t).date() for t in all_dates]  # Need pandas
# Actually, let me use numpy datetime64
all_dates_np = baseline_data.time.values.astype('datetime64[D]')
print("All dates:", all_dates_np[0], "to", all_dates_np[-1])
print("Number of dates:", len(all_dates_np))

# Convert to date objects
import pandas as pd
all_date_objs = [pd.Timestamp(t).date() for t in all_dates_np]
print("First few:", all_date_objs[:3])
