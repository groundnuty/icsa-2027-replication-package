
import numpy as np
from datetime import date
import json

intermediate_dir = 'intermediate'

# Load metadata and data
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

# Find a sea cell that is hot on day 43 (July 14) to verify MHW detection
# Let me find cells that are hot on day 43
hot_day43 = hot[43]
hot_cells_43 = np.argwhere(hot_day43)
print(f"Cells hot on day 43: {len(hot_cells_43)}")

if len(hot_cells_43) > 0:
    # Pick the first one and trace its hot pattern
    la, lo = hot_cells_43[0]
    print(f"Cell ({la}, {lo}) hot pattern (day 35-75):")
    for i in range(35, min(75, n_days)):
        print(f"  Day {i} ({target_dates[i]}): hot={hot[i, la, lo]}")
