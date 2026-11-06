
import numpy as np

# Load intermediate results
threshold = np.load('threshold_raw.npy')  # (367, 60, 60)
climatology = np.load('climatology_raw.npy')  # (367, 60, 60)
sea_cells = np.load('sea_cells.npy')

# Smooth with 31-day centered moving mean wrapping around the year
# For day d (1-366), average days d-15 to d+15 (modulo 366)
# In 0-based indexing (arrays have size 367, index 0 unused), day d is at index d

# We need to smooth only the sea cells
threshold_smooth = np.full((367, 60, 60), np.nan)
climatology_smooth = np.full((367, 60, 60), np.nan)

sea_indices = np.where(sea_cells)
n_sea = len(sea_indices[0])

# Precompute window for each day
for d in range(1, 367):
    window = []
    for offset in range(-15, 16):
        day_idx = ((d - 1 + offset) % 366) + 1  # 1-based day index with modulo 366
        window.append(day_idx)
    
    for k in range(n_sea):
        lat_i, lon_i = sea_indices[0][k], sea_indices[1][k]
        
        # Get the values for the window
        thresh_vals = threshold[window, lat_i, lon_i]
        clim_vals = climatology[window, lat_i, lon_i]
        
        # Check for NaN
        if np.isnan(thresh_vals).any():
            print(f"NaN in threshold window for day {d}, cell ({lat_i}, {lon_i})")
            threshold_smooth[d, lat_i, lon_i] = np.nan
        else:
            threshold_smooth[d, lat_i, lon_i] = np.mean(thresh_vals)
        
        if np.isnan(clim_vals).any():
            print(f"NaN in climatology window for day {d}, cell ({lat_i}, {lon_i})")
            climatology_smooth[d, lat_i, lon_i] = np.nan
        else:
            climatology_smooth[d, lat_i, lon_i] = np.mean(clim_vals)

print("Smoothing done")
# Check for NaN
print(f"NaN in smoothed threshold (sea cells): {np.isnan(threshold_smooth[1:367][:, sea_cells]).sum()}")
print(f"NaN in smoothed climatology (sea cells): {np.isnan(climatology_smooth[1:367][:, sea_cells]).sum()}")

# Save
np.save('threshold_smooth.npy', threshold_smooth)
np.save('climatology_smooth.npy', climatology_smooth)
