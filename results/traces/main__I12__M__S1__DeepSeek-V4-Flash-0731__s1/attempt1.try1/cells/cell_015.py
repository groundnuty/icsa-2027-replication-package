
import numpy as np

threshold = np.load('/tmp/threshold_raw.npy')
climatology = np.load('/tmp/climatology_raw.npy')
n_lat, n_lon = threshold.shape[1], threshold.shape[2]

def smooth_wrap(data):
    """Apply 31-day centered moving mean wrapping around the year.
    data: shape (366, ...)"""
    n = data.shape[0]  # should be 366
    result = np.zeros_like(data, dtype=np.float64)
    
    # Pad: for each day d, we average days d-15 to d+15 modulo 366
    # We'll handle by wrapping
    for d in range(n):
        indices = [(d + offset) % n for offset in range(-15, 16)]
        vals = data[indices]
        result[d] = np.nanmean(vals, axis=0)
    return result

# Apply smoothing
threshold_smooth = smooth_wrap(threshold)
climatology_smooth = smooth_wrap(climatology)

print("Smoothed threshold shape:", threshold_smooth.shape)
print("Smoothed climatology shape:", climatology_smooth.shape)

# Check some values
print("\nSmoothed threshold for cell (30,30):")
for doy in [58, 59, 60, 61, 152, 244]:
    print(f"  Day {doy+1}: {threshold_smooth[doy, 30, 30]:.4f}")

print("\nSmoothed climatology for cell (30,30):")
for doy in [58, 59, 60, 61, 152, 244]:
    print(f"  Day {doy+1}: {climatology_smooth[doy, 30, 30]:.4f}")

np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed threshold and climatology")
