
import numpy as np
import pickle
import datetime

# Load data
target_sst = np.load('/tmp/target_sst.npy').astype(np.float64)
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')
hot = np.load('/tmp/hot.npy')

# Check a few sea cells
sea_idx = np.where(sea_cells)
n_sea = len(sea_idx[0])

# Let's check the first 5 sea cells
for si in range(min(5, n_sea)):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    print(f"\nCell ({li},{loi}):")
    print(f"  Target SST (first 10 days): {target_sst[:10, li, loi]}")
    print(f"  Threshold (doy 153-162): {threshold_smooth[152:162, li, loi]}")
    print(f"  Hot days count: {hot[:, li, loi].sum()}")
    print(f"  MHW days count: {mhw_mask[:, li, loi].sum()}")
    # Find MHWs
    runs = []
    i = 0
    while i < 92:
        if hot[i, li, loi]:
            j = i
            while j < 92 and hot[j, li, loi]:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    print(f"  Hot runs: {runs}")
    # Check threshold for target days
    # Jun 1 = doy 153, index 152
    print(f"  SST on Jun 1: {target_sst[0, li, loi]:.2f} K, Threshold: {threshold_smooth[152, li, loi]:.2f} K, Hot: {hot[0, li, loi]}")
    print(f"  SST on Jun 15: {target_sst[14, li, loi]:.2f} K, Threshold: {threshold_smooth[166, li, loi]:.2f} K, Hot: {hot[14, li, loi]}")
    print(f"  SST on Jul 1: {target_sst[30, li, loi]:.2f} K, Threshold: {threshold_smooth[182, li, loi]:.2f} K, Hot: {hot[30, li, loi]}")
    print(f"  SST on Aug 1: {target_sst[61, li, loi]:.2f} K, Threshold: {threshold_smooth[213, li, loi]:.2f} K, Hot: {hot[61, li, loi]}")
    print(f"  SST on Aug 31: {target_sst[91, li, loi]:.2f} K, Threshold: {threshold_smooth[243, li, loi]:.2f} K, Hot: {hot[91, li, loi]}")
