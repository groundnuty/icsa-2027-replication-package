
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Load data
sst_data = np.load('/tmp/sst_data.npy')  # (15340, 60, 60) float64
times_int = np.load('/tmp/times.npy')    # int64 days since epoch
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

times = pd.to_datetime(times_int, unit='D')
n_times = len(times)

print("Data loaded:", sst_data.shape, sst_data.dtype)
print("Time range:", times[0], "to", times[-1])

# Compute day of year using custom mapping
def compute_doy(month, day):
    if month == 1:
        return day
    elif month == 2:
        return 31 + day
    else:
        days_before = 60
        days_in_month = {3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
        for m in range(3, month):
            days_before += days_in_month[m]
        return days_before + day

# Compute doy for all times
doy_all = np.array([compute_doy(t.month, t.day) for t in times], dtype=np.int32)
print("doy values:", doy_all.min(), doy_all.max())
# Verify some values
print("Jan 1:", compute_doy(1,1))
print("Feb 28:", compute_doy(2,28))
print("Feb 29:", compute_doy(2,29))
print("Mar 1:", compute_doy(3,1))
print("Dec 31:", compute_doy(12,31))
