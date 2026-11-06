
import numpy as np
import pandas as pd

mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_indices = np.load('/tmp/target_indices.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')

# Check active days
active = (mhw_mask.sum(axis=0) > 0)
print("Active days (target indices):", np.where(active)[0])
for idx in np.where(active)[0]:
    date = times[target_indices[idx]].date()
    n_cells = mhw_mask[:, idx].sum()
    print(f"  Day {idx} ({date}): {n_cells} cells in MHW")

# Check cells active on day 30 (July 1) but not day 29
cells_on_30 = np.where(mhw_mask[:, 30] > 0)[0]
print(f"\nCells active on day 30 (July 1): {len(cells_on_30)}")
for ci in cells_on_30[:5]:
    lat, lon = sea_cells[ci]
    print(f"  Cell ({lat},{lon}): MHW days = {np.where(mhw_mask[ci] > 0)[0]}")
