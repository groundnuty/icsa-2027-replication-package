
import numpy as np
from datetime import date

# Reload everything
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smoothed = np.load('/tmp/threshold_smoothed.npy')
cell_mhw = np.load('/tmp/cell_mhw.npy')

with open('/tmp/target_dates.txt') as f:
    target_dates_str = [line.strip() for line in f]
target_dates = [date.fromisoformat(s) for s in target_dates_str]

# Check some specific sea cells
# Find a few sea cell indices
sea_idx = np.argwhere(sea_cells)
print(f"First 5 sea cell indices: {sea_idx[:5]}")

# Check cell (30, 30) if it's a sea cell
if sea_cells[30, 30]:
    print(f"\nCell (30,30) is a sea cell")
    # Check its MHW status over target period
    mhw_days = np.where(cell_mhw[:, 30, 30])[0]
    if len(mhw_days) > 0:
        print(f"MHW days for cell (30,30): indices {mhw_days[0]} to {mhw_days[-1]}")
        print(f"Dates: {target_dates[mhw_days[0]].isoformat()} to {target_dates[mhw_days[-1]].isoformat()}")
        print(f"Number of MHW days: {len(mhw_days)}")
    else:
        print("No MHW for cell (30,30)")

# Check a cell that might not be in an MHW
# Let me look at the per-cell MHW pattern
# For each cell, count MHW days
mhw_counts = cell_mhw.sum(axis=0)
print(f"\nMHW day counts per cell:")
print(f"  Min: {mhw_counts.min()}, Max: {mhw_counts.max()}, Mean: {mhw_counts[sea_cells].mean():.1f}")
print(f"  Cells with 0 MHW days: {(mhw_counts == 0).sum()}")
print(f"  Cells with >0 MHW days: {(mhw_counts > 0).sum()}")
