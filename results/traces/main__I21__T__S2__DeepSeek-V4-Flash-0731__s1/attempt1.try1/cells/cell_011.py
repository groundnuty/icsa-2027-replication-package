
import numpy as np
import pandas as pd
from datetime import datetime

# Load intermediate results
threshold_smooth = np.load('threshold_smooth.npy')
climatology_smooth = np.load('climatology_smooth.npy')
sea_cells = np.load('sea_cells.npy')

# Load target data
target_data = xr.open_dataset('target_data.nc')
target_sst = target_data.analysed_sst.values
target_time = target_data.time.values

print("Target time values:")
for t in target_time[:5]:
    print(f"  {pd.Timestamp(t)}")
print("  ...")
for t in target_time[-3:]:
    print(f"  {pd.Timestamp(t)}")

# Map each target date to day of year
def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month] + day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = [day_of_year(dt) for dt in target_dates]
print(f"\nTarget day-of-year values: {target_doy}")
print(f"Target period: {target_dates[0]} to {target_dates[-1]}")

# Check: 2021 is not a leap year, so June 1 is day 152+1=153? Let me verify
# Jan=31, Feb=28, Mar=31, Apr=30, May=31 = 151 days before June
# So June 1 = 152
# Using our scheme: cum_days[6]=152, so June 1 = 152+1 = 153

# Aug 31: cum_days[8]=213, so 213+31 = 244
print(f"\nJune 1 2021: day {target_doy[0]} (expected ~153)")
print(f"Aug 31 2021: day {target_doy[-1]} (expected ~244)")
