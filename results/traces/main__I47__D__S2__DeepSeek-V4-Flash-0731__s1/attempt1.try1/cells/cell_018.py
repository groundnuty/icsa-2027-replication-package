
import numpy as np
import pickle
from datetime import date, timedelta

def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

tgt_data = np.load('/work/tgt_data.npy')
tgt_time = np.load('/work/tgt_time.npy')
threshold_sm = np.load('/work/threshold_sm.npy')
climatology_sm = np.load('/work/climatology_sm.npy')

target_dates = [date(1970,1,1) + timedelta(days=int(t)) for t in tgt_time]
target_doy = np.array([day_of_year(d.month, d.day) for d in target_dates])

tgt_nan = np.isnan(tgt_data)
cell_tgt_nan = tgt_nan.any(axis=0)
sea_cells = ~cell_tgt_nan

# Check a specific sea cell
# Find first sea cell
si, sj = np.where(sea_cells)
print("First sea cell:", si[0], sj[0])

i, j = si[0], sj[0]
# For each target day, compare SST vs threshold
print(f"Cell ({i},{j}): lat={64.4+i*0.02:.2f}, lon={23.42+j*0.02:.2f}")
print("Day | Date | SST | Threshold | Hot")
for t in range(len(target_dates)):
    d = target_doy[t] - 1
    sst = tgt_data[t, i, j]
    th = threshold_sm[d, i, j]
    hot = sst >= th
    if hot or t % 10 == 0:
        print(f"{t+1:3d} | {target_dates[t]} | {sst:.4f} | {th:.4f} | {hot}")
