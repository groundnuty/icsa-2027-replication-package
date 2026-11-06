
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Load data
target_time = np.load('/tmp/target_time.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
target_sst = np.load('/tmp/target_sst.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = np.array([doy_from_date(d) for d in target_dates])

print("Target date to DOY mapping:")
for i in [0, 30, 60, 91]:
    print(f"  {target_dates[i].strftime('%Y-%m-%d')}: DOY {target_doy[i]}")

# Verify that June 1 = 153, July 1 = 183, Aug 1 = 214
print(f"\nExpected: June 1 = 153 (actual: {target_doy[0]})")
print(f"Expected: July 1 = 183 (actual: {target_doy[30]})")  
print(f"Expected: Aug 1 = 214 (actual: {target_doy[61]})")
print(f"Expected: Aug 31 = 244 (actual: {target_doy[91]})")
