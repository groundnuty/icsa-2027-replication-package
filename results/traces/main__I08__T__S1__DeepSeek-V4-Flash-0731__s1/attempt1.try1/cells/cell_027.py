
import numpy as np

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
target_data = np.load('/tmp/target_data.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')
tgt_times = np.load('/tmp/tgt_times.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')
hot = np.load('/tmp/hot.npy')

# Pick a sea cell that's in an MHW
sea_indices = np.where(sea_mask)
# Find a cell that has an MHW
cells_in_mhw = np.where(np.any(mhw_mask > 0, axis=0))
print("Cells with MHW:", len(cells_in_mhw[0]))
if len(cells_in_mhw[0]) > 0:
    i, j = cells_in_mhw[0][0], cells_in_mhw[1][0]
    print(f"Example cell ({i},{j})")
    
    # Show hot pattern and MHW mask for this cell
    print("Day | Date        | SST       | Threshold | Hot | MHW")
    for t in range(len(tgt_times)):
        d = tgt_doy[t]
        sst = target_data[t, i, j]
        th = threshold_smooth[d, i, j]
        is_hot = hot[t, i, j]
        is_mhw = mhw_mask[t, i, j]
        print(f"{t:3d} | {str(tgt_times[t])[:10]} | {sst:9.4f} | {th:9.4f} | {'Y' if is_hot else 'N'} | {is_mhw}")
