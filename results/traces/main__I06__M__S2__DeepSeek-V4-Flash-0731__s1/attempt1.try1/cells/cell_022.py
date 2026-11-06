
import numpy as np

# Load
threshold_raw = np.load('/tmp/threshold_raw.npy')
clim_raw = np.load('/tmp/clim_raw.npy')

# Set day 60 to mean of days 59 and 61
threshold_raw[60] = (threshold_raw[59] + threshold_raw[61]) / 2
clim_raw[60] = (clim_raw[59] + clim_raw[61]) / 2

def smooth_wrap(arr_367):
    """Smooth a 367-length array (index 0 unused, 1..366 = doy)."""
    vals = arr_367[1:367]  # (366, 60, 60)
    n = 366
    result = np.zeros_like(vals)
    for d in range(n):
        indices = [(d + offset) % n for offset in range(-15, 16)]
        result[d] = np.nanmean(vals[indices], axis=0)
    smoothed = np.full_like(arr_367, np.nan)
    smoothed[1:367] = result
    return smoothed

threshold_smooth = smooth_wrap(threshold_raw)
clim_smooth = smooth_wrap(clim_raw)

print("Done smoothing")
print("NaN in smoothed threshold:", np.isnan(threshold_smooth[1:367]).sum())
print("NaN in smoothed clim:", np.isnan(clim_smooth[1:367]).sum())

# Check sea cells
sea_cells = np.load('/tmp/sea_cells.npy')
sea_nan_smooth = np.isnan(threshold_smooth[1:367]).any(axis=0)
print("Sea cells with NaN in smoothed threshold:", (sea_nan_smooth & sea_cells).sum())

np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/clim_smooth.npy', clim_smooth)
print("Saved smoothed")
