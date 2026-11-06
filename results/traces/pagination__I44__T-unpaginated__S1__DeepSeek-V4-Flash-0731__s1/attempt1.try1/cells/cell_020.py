import numpy as np
from datetime import date, timedelta
import pickle

# Reload data
target_sst = np.load('/tmp/work/target_sst.npy')
with open('/tmp/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
sea_cells = np.load('/tmp/work/sea_cells.npy')
threshold_smooth = np.load('/tmp/work/threshold_smooth.npy')
per_cell_mhw = np.load('/tmp/work/per_cell_mhw.npy')
active = np.load('/tmp/work/active_days.npy')

n_target, n_lat, n_lon = target_sst.shape

# Verify: print which cells have MHWs and when
print("Active days:")
for t in range(n_target):
    if active[t]:
        n_cells = per_cell_mhw[t].sum()
        print(f"  {target_dates[t]}: {n_cells} cells in MHW")

# Check which cells are in MHW on active days
print("\nCells in MHW during active period:")
for t in range(n_target):
    if active[t]:
        mhw_cells = np.argwhere(per_cell_mhw[t])
        print(f"  {target_dates[t]}: {len(mhw_cells)} cells")
        if len(mhw_cells) > 0:
            # Show a few
            for c in mhw_cells[:5]:
                print(f"    ({c[0]}, {c[1]})")

# Check: how many hot days per cell
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

for t in range(n_target):
    d = target_dates[t]
    doy = month_day_to_doy(d.month, d.day)
    thresh = threshold_smooth[doy-1]
    hot[t] = (target_sst[t] >= thresh) & sea_cells

print(f"\nHot days per cell (min, max, mean): {hot.sum(axis=0)[sea_cells].min()}, {hot.sum(axis=0)[sea_cells].max()}, {hot.sum(axis=0)[sea_cells].mean():.1f}")

# Check cells that have MHWs
mhw_cells_list = []
for i in range(n_lat):
    for j in range(n_lon):
        if per_cell_mhw[:, i, j].any():
            mhw_cells_list.append((i, j))
print(f"\nCells with at least one MHW: {len(mhw_cells_list)}")
