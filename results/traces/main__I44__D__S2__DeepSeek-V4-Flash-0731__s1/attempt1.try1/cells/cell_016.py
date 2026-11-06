
import numpy as np
import pandas as pd

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')
sea_cells = np.load('/work/sea_cells.npy')
target_data = np.load('/work/target_data.npy')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')

# Target dates
target_start = pd.Timestamp('2004-06-01')
target_end = pd.Timestamp('2004-08-31')
target_dates = pd.date_range(target_start, target_end, freq='D')

# Check which cells are in MHWs during the active days
active_days = [67, 68, 69, 70, 71, 72]
for t in active_days:
    cells = np.argwhere(mhw_mask[t] == 1)
    print(f"Day {t} ({target_dates[t].date()}): {len(cells)} cells in MHW")

# Check a sample cell
# Find a cell that's in an MHW
sample_cells = np.argwhere(mhw_mask.sum(axis=0) > 0)
print(f"\nCells with MHW activity: {len(sample_cells)}")
if len(sample_cells) > 0:
    lat_i, lon_i = sample_cells[0]
    print(f"Sample cell: lat={lat_i}, lon={lon_i}")
    
    # Check its hot days and MHW pattern
    hot_cell = target_data[:, lat_i, lon_i]
    doys = []
    for dt in target_dates:
        def doy(month, day):
            offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
            return offsets[month-1] + day
        doys.append(doy(dt.month, dt.day))
    doys = np.array(doys)
    
    thresh = np.array([thresholds_smooth[lat_i, lon_i, d-1] for d in doys])
    
    print(f"  SST range: {np.nanmin(hot_cell):.2f} to {np.nanmax(hot_cell):.2f}")
    print(f"  Threshold range: {np.nanmin(thresh):.2f} to {np.nanmax(thresh):.2f}")
    
    is_hot = hot_cell >= thresh
    print(f"  Hot days: {np.where(is_hot)[0]}")
    print(f"  MHW mask: {np.where(mhw_mask[:, lat_i, lon_i] == 1)[0]}")
