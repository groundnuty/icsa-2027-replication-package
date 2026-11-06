
import numpy as np

def smooth_wrap(arr):
    """Apply unweighted centred 31-day moving mean that wraps around.
    arr shape: (366, n_lat, n_lon)"""
    n_days = 366
    result = np.zeros_like(arr)
    for lat in range(arr.shape[1]):
        for lon in range(arr.shape[2]):
            if np.isfinite(arr[0, lat, lon]):  # it's a sea cell
                for d in range(n_days):
                    # Average days d-15 to d+15 modulo 366
                    window = []
                    for k in range(-15, 16):
                        idx = (d + k) % n_days
                        if np.isfinite(arr[idx, lat, lon]):
                            window.append(arr[idx, lat, lon])
                    result[d, lat, lon] = np.mean(window)
    return result

# Apply smoothing
smoothed_threshold = smooth_wrap(threshold)
smoothed_climatology = smooth_wrap(climatology)

print("Smoothed threshold shape:", smoothed_threshold.shape)
print("Smoothed climatology shape:", smoothed_climatology.shape)

# Verify for a sea cell
# Find first sea cell
sea_cell_indices = np.argwhere(sea_mask)
print("First sea cell:", sea_cell_indices[0])
lat0, lon0 = sea_cell_indices[0]
print(f"Threshold[150] at sea cell ({lat0},{lon0}): {smoothed_threshold[150, lat0, lon0]}")
print(f"Smoothed threshold[150]: {smoothed_threshold[150, lat0, lon0]}")
print(f"Raw threshold[150]: {threshold[150, lat0, lon0]}")
