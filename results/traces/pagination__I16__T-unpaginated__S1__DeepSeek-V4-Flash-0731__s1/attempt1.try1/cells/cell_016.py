
import numpy as np

# Load thresholds and climatology (indices 0-366, using 1-366 for day-of-year)
thresholds = np.load('/tmp/thresholds.npy')  # (367, 3600)
climatology = np.load('/tmp/climatology.npy')  # (367, 3600)

# Extract day-of-year 1-366 as (366, 3600)
thresh_366 = thresholds[1:367]  # (366, 3600)
clim_366 = climatology[1:367]  # (366, 3600)
print('thresh_366 shape:', thresh_366.shape)
print('clim_366 shape:', clim_366.shape)

# Smoothing function
def smooth_wrap(arr_2d):
    """Smooth a (366, N) array with a 31-day centered moving mean wrapping around.
    arr_2d[d, c] corresponds to day-of-year d+1 for cell c."""
    n = 366
    half = 15
    window = 31
    
    # Create extended array with wrapping: 3 copies
    ext = np.tile(arr_2d, (3, 1))  # (1098, N)
    
    # Use sliding window with cumulative sum
    # Handle NaN: use np.nancumsum approach
    # For now, use a simple approach with masking
    result = np.zeros_like(arr_2d)
    
    # Actually, let me just use a direct approach
    for d in range(n):
        start = n + d - half
        result[d] = np.nanmean(ext[start:start+window], axis=0)
    
    return result

# Smooth thresholds and climatology
print('Smoothing thresholds...')
thresh_smooth = smooth_wrap(thresh_366)
print('Smoothing climatology...')
clim_smooth = smooth_wrap(clim_366)

print('Threshold smoothed shape:', thresh_smooth.shape)
print('Climatology smoothed shape:', clim_smooth.shape)

# Check for NaN
print('NaN in smoothed thresholds:', np.isnan(thresh_smooth).sum())
print('NaN in smoothed climatology:', np.isnan(clim_smooth).sum())

# Verify no NaN in valid cells
valid_mask = ~np.all(np.isnan(thresh_smooth), axis=0)
print('Valid cells in thresholds:', valid_mask.sum())
print('All-NaN cells in thresholds:', (~valid_mask).sum())

# Save smoothed results
np.save('/tmp/thresh_smooth.npy', thresh_smooth)
np.save('/tmp/clim_smooth.npy', clim_smooth)
print('Saved smoothed thresholds and climatology')
