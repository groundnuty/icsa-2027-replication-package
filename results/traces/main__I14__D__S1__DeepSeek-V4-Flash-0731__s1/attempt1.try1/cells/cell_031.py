
import numpy as np
import pandas as pd

target_sst = np.load('/work/target_sst.npy')
target_times = np.load('/work/target_times.npy')
target_pd = pd.to_datetime(target_times)
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
per_cell_mhw = np.load('/work/per_cell_mhw.npy')

def doy(date):
    dt = pd.Timestamp(date)
    month = dt.month
    day = dt.day
    month_lengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_lengths[:month-1]) + day

target_doy = np.array([doy(d) for d in target_pd])

# Check cell (44,23)
lat_i, lon_i = 44, 23
sst = target_sst[:, lat_i, lon_i]
print("Cell (44,23):")
print("Day       SST    Thresh   Hot  MHW")
for t in range(30, 45):
    d = target_doy[t]
    thresh = thresholds_smooth[d, lat_i, lon_i]
    hot = sst[t] >= thresh
    mhw = per_cell_mhw[t, lat_i, lon_i]
    print(f"{target_pd[t].date()}  {sst[t]:.2f}  {thresh:.2f}  {hot}  {mhw}")
