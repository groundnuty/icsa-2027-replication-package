
import numpy as np
import pandas as pd

sst_target = np.load('/tmp/sst_target.npy').astype(np.float64)
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
target_dates = np.load('/tmp/target_dates.npy')
target_doy = np.load('/tmp/target_doy.npy')

# Verify cell (15,55)
i, j = 15, 55
print(f"Cell ({i},{j}), sea cell: {sea_cells[i, j]}")

print("\nDate, SST, Threshold, Hot")
for d in range(92):
    date = pd.Timestamp(target_dates[d]).strftime('%Y-%m-%d')
    doy = target_doy[d]
    sst = sst_target[d, i, j]
    thr = threshold_smooth[doy, i, j]
    is_hot = sst >= thr
    if d in range(48, 65):  # July 20 - Aug 5
        print(f"  {date} (doy {doy}): SST={sst:.4f}, Thr={thr:.4f}, Hot={is_hot}")
