import numpy as np

# Load intermediate results
threshold_raw = np.load('/tmp/threshold_raw.npy')  # (367, 60, 60), index 0 unused
climatology_raw = np.load('/tmp/climatology_raw.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

print("threshold_raw shape:", threshold_raw.shape)
print("sea_mask shape:", sea_mask.shape, "sum:", sea_mask.sum())

# Smoothing: 31-day centred moving mean wrapping around
# For DOY array of 366 values, smoothed[d] = mean of days d-15 to d+15 (mod 366)
# Using 1-based DOY: DOY 1 to 366

def smooth_366(arr_366):
    """Smooth a 366-element array with 31-day centred moving mean wrapping around.
    arr_366[d] corresponds to DOY d+1 (0-indexed array).
    """
    # Extend the array by 15 on each side (wrapping)
    # For DOY k (1-based), we want the mean of DOYs k-15 to k+15 (mod 366)
    # In 0-indexed: index k-1, we want indices (k-1-15) mod 366 to (k-1+15) mod 366
    
    # Create extended array
    extended = np.concatenate([arr_366[-15:], arr_366, arr_366[:15]])
    # extended has 396 elements; position 15 to 380 correspond to original 0-365
    
    # For each position in original (0-365), take 31-day window
    smoothed = np.zeros_like(arr_366)
    for i in range(366):
        window = extended[i:i+31]
        smoothed[i] = np.mean(window)
    
    return smoothed

# Apply smoothing per cell
n_lat, n_lon = 60, 60
threshold_smooth = np.zeros((367, n_lat, n_lon), dtype=np.float64)
climatology_smooth = np.zeros((367, n_lat, n_lon), dtype=np.float64)

# For DOYs 1-366, the raw values are in threshold_raw[1:367]
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j]:
            # Extract 366-element array (DOYs 1-366)
            thresh_arr = threshold_raw[1:367, i, j]
            clim_arr = climatology_raw[1:367, i, j]
            
            threshold_smooth[1:367, i, j] = smooth_366(thresh_arr)
            climatology_smooth[1:367, i, j] = smooth_366(clim_arr)

# Check
print("Smoothed threshold[1, i, j] for a sea cell:")
# Find first sea cell
first_sea = np.argwhere(sea_mask)[0]
i0, j0 = first_sea
print(f"First sea cell at ({i0}, {j0})")
print("Raw threshold[1]:", threshold_raw[1, i0, j0])
print("Raw threshold[366]:", threshold_raw[366, i0, j0])
print("Raw threshold[2]:", threshold_raw[2, i0, j0])
print("Smoothed threshold[1]:", threshold_smooth[1, i0, j0])
print("Smoothed threshold[366]:", threshold_smooth[366, i0, j0])
print("Smoothed threshold[2]:", threshold_smooth[2, i0, j0])

# Verify smoothing for a simple case
test = np.arange(366, dtype=np.float64)
smooth_test = smooth_366(test)
print("Smooth test[0]:", smooth_test[0])
print("Expected ~", np.mean(np.arange(366)[[350+i for i in range(15)] + [i for i in range(16)]]))

# Save
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed arrays")
