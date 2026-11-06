
import numpy as np
import datetime

# Reload all needed data
target_sst = np.load('target_sst.npy')
sea_cells = np.load('sea_cells.npy')
threshold_smooth = np.load('threshold_smooth.npy')
clim_smooth = np.load('clim_smooth.npy')
mhw_mask = np.load('mhw_mask.npy')

def date_to_doy(d):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = d.day
    for m in range(1, d.month):
        doy += days_in_month[m-1]
    return doy

target_start = datetime.date(2007, 6, 1)
target_dates = []
d = target_start
for i in range(92):
    target_dates.append(d)
    d += datetime.timedelta(days=1)

# Pick a cell that is in an MHW
sea_indices = np.argwhere(sea_cells)
mhw_cell_indices = np.argwhere(mhw_mask.sum(axis=0) > 0)
print(f"Cells with MHW: {len(mhw_cell_indices)}")

if len(mhw_cell_indices) > 0:
    i, j = mhw_cell_indices[0]
    print(f"\nExamining cell ({i}, {j})")
    
    # Print hot days and MHW days for this cell
    hot_days = []
    for t in range(92):
        doy = date_to_doy(target_dates[t])
        thr = threshold_smooth[doy-1, i, j]
        sst = target_sst[t, i, j]
        is_hot = sst >= thr
        if is_hot:
            hot_days.append((t, str(target_dates[t]), sst, thr, mhw_mask[t, i, j]))
    
    print(f"Hot days for cell ({i},{j}):")
    for t, date, sst, thr, mhw in hot_days:
        print(f"  Day {t} ({date}): sst={sst:.4f}, thr={thr:.4f}, mhw={mhw}")

# Also check the baseline pool for one doy to verify
print("\nVerification of baseline computations:")
# Check doy for a specific date
d = datetime.date(2007, 6, 15)
doy = date_to_doy(d)
print(f"doy({d}) = {doy}")

# Check that threshold_smooth is reasonable
# For a sea cell, look at the threshold for several doys
i, j = sea_indices[0]
print(f"\nThreshold for cell ({i},{j}) for various doys:")
for doy in [1, 60, 100, 153, 180, 200, 244, 300, 366]:
    print(f"  doy={doy}: thr={threshold_smooth[doy-1, i, j]:.4f}, clim={clim_smooth[doy-1, i, j]:.4f}")
