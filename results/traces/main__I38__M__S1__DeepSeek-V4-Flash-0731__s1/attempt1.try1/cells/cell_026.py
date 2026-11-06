
import numpy as np
from datetime import date, timedelta
import json

intermediate_dir = 'intermediate'

with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)
target_dates = [date.fromisoformat(d) for d in meta['target_dates']]

threshold_smooth = np.load(f'{intermediate_dir}/threshold_smooth.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

target_doy = [day_of_year(d) for d in target_dates]
n_days = len(target_dates)

# Compute hot
hot = np.zeros((n_days, 60, 60), dtype=bool)
for i in range(n_days):
    doy = target_doy[i]
    sst = target_sst[i].astype(np.float64)
    th = threshold_smooth[doy - 1]
    hot[i] = (sst >= th) & ~np.isnan(sst)

# Count hot cells per day
for i in range(n_days):
    n_hot = hot[i][sea_cells].sum()
    if n_hot > 0:
        print(f"Day {i} ({target_dates[i]}): {n_hot} hot cells out of {sea_cells.sum()}")
