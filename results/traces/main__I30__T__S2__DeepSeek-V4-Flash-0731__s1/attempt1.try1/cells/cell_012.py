
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

# Define day-of-year mapping (leap year style regardless of actual year)
def doy_from_date(dt):
    """Map a datetime to day of year 1-366 using leap-year calendar."""
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

# Convert baseline_time to datetime objects
baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

# Compute day-of-year for each baseline date
base_doy = np.array([doy_from_date(d) for d in baseline_dates])
print("Baseline DOY range:", base_doy.min(), base_doy.max())
print("Baseline dates with DOY 60:", sum(base_doy == 60))
print("Baseline dates with DOY 59:", sum(base_doy == 59))
print("Baseline dates with DOY 61:", sum(base_doy == 61))

# Identify sea cells: finite on all target days
sea_mask = ~np.isnan(target_sst).any(axis=0)
print("Sea cells:", sea_mask.sum())

# Convert to float64
baseline_sst64 = baseline_sst.astype(np.float64)
target_sst64 = target_sst.astype(np.float64)
