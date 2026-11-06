
import numpy as np

thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')
target_arr = np.load('/work/target_arr.npy')
sea_mask = np.all(np.isfinite(target_arr), axis=0)

# Check if any sea cells have NaN thresholds on any day
for d in range(366):
    nan_sea = np.isnan(thresholds[d]) & sea_mask
    if nan_sea.sum() > 0:
        print(f"Day {d+1}: {nan_sea.sum()} sea cells with NaN threshold")
        break
else:
    print("All sea cells have valid thresholds for all days")

# Check land cells
for d in range(366):
    nan_land = np.isnan(thresholds[d]) & ~sea_mask
    if nan_land.sum() > 0:
        print(f"Day {d+1}: {nan_land.sum()} land cells with NaN threshold")
        break
else:
    print("All land cells have NaN thresholds for all days")
