
import numpy as np

# Load
threshold_raw = np.load('/tmp/threshold_raw.npy')  # (367, 60, 60)
clim_raw = np.load('/tmp/clim_raw.npy')

# Set day 60 to mean of days 59 and 61
threshold_raw[60] = (threshold_raw[59] + threshold_raw[61]) / 2
clim_raw[60] = (clim_raw[59] + clim_raw[61]) / 2

# Verify
print("Day 59:", threshold_raw[59, 50, 30], clim_raw[59, 50, 30])
print("Day 60:", threshold_raw[60, 50, 30], clim_raw[60, 50, 30])
print("Day 61:", threshold_raw[61, 50, 30], clim_raw[61, 50, 30])

# Now smooth with 31-day centered moving average wrapping around year
# Day d averages days d-15 to d+15, counted modulo 366.
# We work with indices 1..366 (doy). 
# For each d in 1..366, average days ((d-15)..(d+15)) mod 366 (but with 1-based indexing)

def smooth_wrap(arr_367):
    """Smooth a 367-length array (index 0 unused, 1..366 = doy)."""
    # Extract the 366 values
    vals = arr_367[1:367]  # shape (366, 60, 60)
    n = 366
    result = np.zeros_like(vals)
    
    for d in range(n):  # 0-based, representing doy d+1
        # Days d-15 to d+15 (0-based), wrapping modulo 366
        indices = [(d + offset) % n for offset in range(-15, 16)]
        result[d] = np.nanmean(vals[indices], axis=0)
    
    # Put back
    smoothed = np.full_like(arr_367, np.nan)
    smoothed[1:367] = result
    return smoothed

threshold_smooth = smooth_wrap(threshold_raw)
clim_smooth = smooth_wrap(clim_raw)

print("Smoothed values:")
print("Day 153 threshold:", threshold_smooth[153, 50, 30])
print("Day 153 clim:", clim_smooth[153, 50, 30])

# Verify wrapping: day 1 should average days 352-16 (mod 366)
# Actually 1-15 = -14 to -1 → days 353-366 (0-based: 352-365), plus 1-16 → days 1-16
# Check some values
print("Day 1 raw threshold:", threshold_raw[1, 50, 30])
print("Day 1 smoothed threshold:", threshold_smooth[1, 50, 30])

# Save
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/clim_smooth.npy', clim_smooth)
print("Saved smoothed threshold and climatology")
