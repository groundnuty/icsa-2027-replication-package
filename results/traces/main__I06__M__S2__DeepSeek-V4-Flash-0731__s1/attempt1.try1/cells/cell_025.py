
import numpy as np
import pandas as pd

hot = np.load('/tmp/hot.npy')
mhw_cell = np.load('/tmp/mhw_cell.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_dates = np.load('/tmp/target_dates.npy')
target_doy = np.load('/tmp/target_doy.npy')

# Find cells with MHW
cells_with_mhw = np.where(mhw_cell.any(axis=0))
print(f"Cells with MHW: {len(cells_with_mhw[0])}")
for k in range(len(cells_with_mhw[0])):
    i, j = cells_with_mhw[0][k], cells_with_mhw[1][k]
    days_in_mhw = np.where(mhw_cell[:, i, j])[0]
    dates = [pd.Timestamp(target_dates[d]).strftime('%Y-%m-%d') for d in days_in_mhw]
    print(f"  Cell ({i},{j}): MHW days {days_in_mhw[0]}-{days_in_mhw[-1]}: {dates[0]} to {dates[-1]}, {len(days_in_mhw)} days")
