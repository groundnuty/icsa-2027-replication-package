
import numpy as np
from datetime import date, timedelta

# Load data
target_sst = np.load('/tmp/target_sst.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
thr_smooth = np.load('/tmp/thr_smooth.npy')
cli_smooth = np.load('/tmp/cli_smooth.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')

# Day-of-year mapping
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)

def date_to_doy(d):
    return cum_days[d.month - 1] + d.day

# Pick a sea cell and check its values
sea_indices = np.where(sea_cells)
si, sj = sea_indices[0][0], sea_indices[1][0]

# Get the target dates
target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

print(f"=== Cell ({si}, {sj}) ===")
print(f"Sea cell: {sea_cells[si, sj]}")

# Check SST and threshold for each target day
for t in range(len(target_dates)):
    doy = date_to_doy(target_dates[t])
    sst = target_sst[t, si, sj]
    thr = thr_smooth[doy-1, si, sj]
    cli = cli_smooth[doy-1, si, sj]
    hot = sst >= thr
    in_mhw = mhw_mask[t, si, sj] == 1
    if hot or in_mhw:
        print(f"  {target_dates[t]} (doy {doy}): SST={sst:.4f}, thr={thr:.4f}, cli={cli:.4f}, hot={hot}, MHW={in_mhw}")
