import numpy as np

target_data = np.load('/work/target_data.npy').astype(np.float64)
threshold_smooth = np.load('/work/threshold_smooth.npy')

# Look at a specific sea cell
# Find the first sea cell
sea_mask = np.all(~np.isnan(target_data), axis=0)
sea_cells = np.argwhere(sea_mask)
print("First sea cell:", sea_cells[0])

i, j = sea_cells[0]
print(f"Cell ({i}, {j})")

# Check target SST values
print("\nTarget SST (all 92 days):")
print(target_data[:, i, j])

# Check threshold values
print("\nThreshold (target DOYs 153-244):")
print(threshold_smooth[i, j, 152:244])

# Check which days are hot
print("\nHot days:")
for t in range(92):
    doy = 153 + t
    is_hot = target_data[t, i, j] >= threshold_smooth[i, j, doy-1]
    if is_hot:
        print(f"  Day {t} (DOY {doy}): SST={target_data[t, i, j]:.2f}, thresh={threshold_smooth[i, j, doy-1]:.2f}")
