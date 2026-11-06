
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

# First sea cell
sea_cells = np.all(np.isfinite(target_sst), axis=0)
sea_indices = np.where(sea_cells)
first_sea = (sea_indices[0][0], sea_indices[1][0])
print(f"First sea cell: ({first_sea[0]}, {first_sea[1]})")

lat_i, lon_i = first_sea
sst = target_sst[:, lat_i, lon_i]
thresh = np.array([thresholds_smooth[target_doy[t], lat_i, lon_i] for t in range(len(target_pd))])
hot = sst >= thresh
mhw = per_cell_mhw[:, lat_i, lon_i]

print("Day  SST    Thresh  Hot  MHW")
for t in range(len(target_pd)):
    print(f"{str(target_pd[t].date())}  {sst[t]:.2f}  {thresh[t]:.2f}  {hot[t]}  {mhw[t]}")
