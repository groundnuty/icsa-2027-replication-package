
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load data
target_sst = np.load('/work/target_sst.npy')
targ_times = np.load('/work/targ_times.npy')
thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')

targ_dates = pd.DatetimeIndex(targ_times)
n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
n_targ = len(targ_dates)

# Day of year mapping
def date_to_doy(dt):
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

targ_doy = np.array([date_to_doy(d) for d in targ_dates])

# Check threshold for each target doy
print("Thresholds for target doys (cell 0,0):")
for t in range(0, 92, 10):
    d = targ_doy[t]
    print(f"  Day {t} ({targ_dates[t].strftime('%Y-%m-%d')}, doy {d}): threshold={thresholds[d-1, 0, 0]:.4f}")

# Check hot status for cell 0,0
print(f"\nCell (0,0):")
for t in range(0, 92):
    d = targ_doy[t]
    sst = target_sst[t, 0, 0]
    thr = thresholds[d-1, 0, 0]
    is_hot = sst >= thr
    if is_hot:
        print(f"  Day {t} ({targ_dates[t].strftime('%Y-%m-%d')}): SST={sst:.4f}, thr={thr:.4f}, HOT")
