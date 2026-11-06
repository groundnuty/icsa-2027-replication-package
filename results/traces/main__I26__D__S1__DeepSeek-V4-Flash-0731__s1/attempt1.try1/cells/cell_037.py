import numpy as np

threshold_smooth = np.load('/work/threshold_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')

# Check for NaN in threshold
print(f"Threshold NaN count: {np.sum(np.isnan(threshold_smooth))}")
print(f"Threshold total elements: {threshold_smooth.size}")

# Check for sea cells only
target_data = np.load('/work/target_data.npy').astype(np.float64)
sea_mask = np.all(~np.isnan(target_data), axis=0)

# Check which sea cells have NaN thresholds for any target DOY
target_doy_range = range(153, 245)  # DOYs 153-244
sea_cells = np.argwhere(sea_mask)

nan_cells = []
for i, j in sea_cells:
    for doy in target_doy_range:
        if np.isnan(threshold_smooth[i, j, doy-1]):
            nan_cells.append((i, j, doy))
            break

print(f"Sea cells with NaN threshold in target period: {len(nan_cells)}")
if nan_cells:
    print("First few:", nan_cells[:5])

# Check for NaN in climatology
print(f"\nClimatology NaN count: {np.sum(np.isnan(climatology_smooth))}")

nan_cells_c = []
for i, j in sea_cells:
    for doy in target_doy_range:
        if np.isnan(climatology_smooth[i, j, doy-1]):
            nan_cells_c.append((i, j, doy))
            break
print(f"Sea cells with NaN climatology in target period: {len(nan_cells_c)}")
if nan_cells_c:
    print("First few:", nan_cells_c[:5])
