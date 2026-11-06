
import numpy as np

thresholds = np.load('thresholds_raw.npy')
climatologies = np.load('climatologies_raw.npy')

def smooth_wrap(arr):
    """Apply centred 31-day moving mean wrapping around a 366-element array along axis 0."""
    n = 366
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)  # (396, 60, 60)
    result = np.zeros((n, 60, 60), dtype=np.float64)
    for i in range(n):
        result[i] = np.mean(padded[i:i+31], axis=0)
    return result

# Apply smoothing
thresholds_smooth = smooth_wrap(thresholds)
climatologies_smooth = smooth_wrap(climatologies)

print("Smoothed thresholds shape:", thresholds_smooth.shape)
print("Smoothed climatologies shape:", climatologies_smooth.shape)
print("NaN in smoothed thresholds:", np.isnan(thresholds_smooth).sum())
print("NaN in smoothed climatologies:", np.isnan(climatologies_smooth).sum())

# Check sample values
print("Smoothed threshold (doy 153, cell 0,0):", thresholds_smooth[152, 0, 0])
print("Smoothed climatology (doy 153, cell 0,0):", climatologies_smooth[152, 0, 0])

# Save
np.save('thresholds_smooth.npy', thresholds_smooth)
np.save('climatologies_smooth.npy', climatologies_smooth)
