
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

# Find cells with MHW on July 1 (t=30)
t_jul1 = 30
cells_jul1 = np.where(per_cell_mhw[t_jul1])
print(f"Cells with MHW on July 1: {len(cells_jul1[0])}")
for i in range(min(len(cells_jul1[0]), 3)):
    lat_i, lon_i = cells_jul1[0][i], cells_jul1[1][i]
    print(f"  Cell ({lat_i},{lon_i})")
    # Print hot/MHW status for this cell around July 1
    sst = target_sst[:, lat_i, lon_i]
    for t in range(max(0, t_jul1-7), min(92, t_jul1+10)):
        d = target_doy[t]
        thresh = thresholds_smooth[d, lat_i, lon_i]
        hot = sst[t] >= thresh
        mhw = per_cell_mhw[t, lat_i, lon_i]
        print(f"    {target_pd[t].date()}: SST={sst[t]:.2f}, Thresh={thresh:.2f}, Hot={hot}, MHW={mhw}")
