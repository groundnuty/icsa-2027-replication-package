import numpy as np

threshold = np.load('/tmp/work/threshold_raw.npy')
climatology = np.load('/tmp/work/climatology_raw.npy')

print(f"threshold shape: {threshold.shape}")

def smooth_366_fast(arr):
    """Efficiently smooth a (366, ...) array along axis 0 with 31-day centered moving mean."""
    n = arr.shape[0]
    # Pad with wrap-around: 15 before and 15 after
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    
    result = np.zeros_like(arr)
    for i in range(n):
        # Original day i is at padded index 15 + i
        # Window: padded indices (15+i-15) to (15+i+15), inclusive => indices i to i+30
        # In padded coordinates: days i-15+15 = i to i+15+15 = i+30
        # Wait, let me think again.
        # Original day index i corresponds to padded index 15+i.
        # We want days (i-15) mod 366 to (i+15) mod 366.
        # In padded coordinates, day (i-15) mod 366 is at index 15 + ((i-15) mod 366).
        # But since padded has 15 prepended (original days 351-365) and 15 appended (original days 0-14),
        # day (i-15) mod 366 is at padded index i.
        # Day (i+15) mod 366 is at padded index i+30.
        # So window in padded: indices i to i+30 (31 values).
        window = padded[i:i+31]
        result[i] = np.mean(window, axis=0)
    
    return result

# Test on a small array
test = np.arange(366, dtype=np.float64)
smoothed_test = smooth_366_fast(test)

# Day 0 (index 0): averages days (0-15) mod 366 to (0+15) mod 366 = days 351..365, 0..15
vals_0 = np.concatenate([np.arange(351, 366), np.arange(0, 16)])
expected_0 = np.mean(vals_0)
print(f"Test day 0: {smoothed_test[0]:.4f}, expected: {expected_0:.4f}")
assert np.isclose(smoothed_test[0], expected_0), f"Smoothing test failed! {smoothed_test[0]} vs {expected_0}"

# Day 100: averages days 85-115
expected_100 = np.mean(np.arange(85, 116))
print(f"Test day 100: {smoothed_test[100]:.4f}, expected: {expected_100:.4f}")
assert np.isclose(smoothed_test[100], expected_100), "Smoothing test failed!"

# Day 365 (index 365): averages days 350-365, 0-14
vals_365 = np.concatenate([np.arange(350, 366), np.arange(0, 15)])
expected_365 = np.mean(vals_365)
print(f"Test day 365: {smoothed_test[365]:.4f}, expected: {expected_365:.4f}")
assert np.isclose(smoothed_test[365], expected_365), "Smoothing test failed!"

print("Smoothing test passed!")

# Apply smoothing to threshold and climatology
threshold_smooth = smooth_366_fast(threshold)
climatology_smooth = smooth_366_fast(climatology)

print(f"threshold_smooth shape: {threshold_smooth.shape}")
print(f"climatology_smooth shape: {climatology_smooth.shape}")

# Save smoothed results
np.save('/tmp/work/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/work/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed threshold and climatology.")

# Find a sea cell and check values
sea_cells = np.isfinite(threshold_smooth[0])
print(f"Sea cells on day 1: {sea_cells.sum()}")
if sea_cells.sum() > 0:
    idx = np.argwhere(sea_cells)[0]
    print(f"First sea cell at lat,lon: ({region_lat[idx[0]]:.2f}, {region_lon[idx[1]]:.2f})")
    print(f"  Threshold day 153: {threshold_smooth[152, idx[0], idx[1]]}")
    print(f"  Climatology day 153: {climatology_smooth[152, idx[0], idx[1]]}")
