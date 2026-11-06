
import numpy as np

hot = np.load('/tmp/hot.npy') if False else None

# Let me redo the hot matrix computation
import numpy as np
import pandas as pd
from datetime import timedelta

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_time = np.load('/tmp/target_time.npy')

def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = np.array([doy_from_date(d) for d in target_dates])
target_sst64 = target_sst.astype(np.float64)

n_time = len(target_dates)
n_lat, n_lon = 60, 60

# Create hot matrix
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    doy = target_doy[t] - 1  # 0-indexed
    thr = threshold_smooth[doy]
    sst_t = target_sst64[t]
    hot[t] = (sst_t >= thr) & sea_mask

np.save('/tmp/hot.npy', hot)
print("Hot matrix shape:", hot.shape)
print("Hot cells:", hot.sum())
