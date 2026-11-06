
import numpy as np
from datetime import datetime, timezone, timedelta

# Load data
target_sst = np.load('output/target_sst.npy')
sea_cells = np.load('output/sea_cells.npy')
threshold_smooth = np.load('output/threshold_smooth.npy')
mhw_mask = np.load('output/mhw_mask.npy')

# Check cell (0,0)
lat, lon = 0, 0
print(f"Cell ({lat},{lon}) - sea cell: {sea_cells[lat, lon]}")

# Check if cell is in an MHW and when
mhw_cell = mhw_mask[:, lat, lon]
hot_days = np.where(mhw_cell > 0)[0]
print(f"MHW days for cell ({lat},{lon}): {hot_days}")

if len(hot_days) > 0:
    # Check SST >= threshold on MHW days
    sst_cell = target_sst[hot_days[0], lat, lon]
    
    # Get day of year for this target day
    target_start = datetime(2014, 6, 1, tzinfo=timezone.utc)
    day_dt = target_start + timedelta(days=hot_days[0])
    starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    d_doy = starts[day_dt.month] + day_dt.day
    thr = threshold_smooth[d_doy - 1, lat, lon]
    
    print(f"First MHW day: {hot_days[0]} = {day_dt.date()}, doy={d_doy}")
    print(f"SST: {sst_cell:.4f}, Threshold: {thr:.4f}")
    print(f"SST >= Threshold: {sst_cell >= thr}")

# Check how many cells have MHWs and their distribution
cells_with_mhw = (mhw_mask.sum(axis=0) > 0)
print(f"\nCells with MHWs: {cells_with_mhw.sum()} / {sea_cells.sum()} sea cells")

# Check if all sea cells have MHWs
print(f"All sea cells have MHWs: {np.all(cells_with_mhw[sea_cells])}")

# Check the active days (at least one cell in MHW)
active = mhw_mask.sum(axis=(1, 2)) > 0
print(f"\nActive days (out of {len(active)}): {active.sum()}")
print(f"First active day: {np.where(active)[0][0]}")
print(f"Last active day: {np.where(active)[0][-1]}")
print(f"All days between first and last active are active: {np.all(active[np.where(active)[0][0]:np.where(active)[0][-1]+1])}")
