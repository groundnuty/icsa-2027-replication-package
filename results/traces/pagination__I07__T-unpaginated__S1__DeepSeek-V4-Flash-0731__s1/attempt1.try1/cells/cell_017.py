
import numpy as np
import time

# Load raw thresholds and climatologies
threshold_raw = np.load('/tmp/threshold_raw.npy')  # (366, 60, 60)
climatology_raw = np.load('/tmp/climatology_raw.npy')

print(f"Threshold shape: {threshold_raw.shape}")
print(f"Climatology shape: {climatology_raw.shape}")

def smooth_31day(arr):
    """Apply unweighted centred 31-day moving mean that wraps around the year.
    arr: (366, ...) array. Day d averages days d-15 ... d+15 (modulo 366)."""
    n = 366
    # Extend the array to handle wrapping
    # We need indices from d-15 to d+15 for d from 0 to 365
    # Indices range from -15 to 380
    # Pad by 15 on each side, wrapping around
    
    # Create extended array: indices -15 to 380 (total 366+30 = 396 values)
    # Actually, let me use np.roll to create the extended array
    ext = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)  # (396, ...)
    
    result = np.zeros_like(arr)
    for d in range(n):
        # Original index d corresponds to extended index 15+d
        # We average from 15+d-15 to 15+d+15 = d to d+30 in extended
        # Wait, that's not right. Let me think again.
        # For day d (0-based), we average days (d-15) mod 366 to (d+15) mod 366
        # In the extended array, day d is at position 15+d
        # We average positions (15+d-15) to (15+d+15) = d to d+30 in extended
        # But the extended array has 396 positions (indices 0-395)
        # Position 15+d ranges from 15 to 380
        # We average positions (15+d-15) to (15+d+15) = d to d+30
        
        # Actually, I think it's simpler to use numpy operations directly
        # Let me construct the result using a cumulative sum approach or direct indexing
        
        # Direct approach: for day d, the 31 days are (d-15) to (d+15) mod 366
        # In extended array (which has original array preceded by 15 days and followed by 15 days):
        # Original day d is at extended index 15+d
        # Days d-15 to d+15 are at extended indices d to d+30
        
        result[d] = np.mean(ext[d:d+31], axis=0)
    
    return result

# Test on a simple 1D array
test = np.arange(366, dtype=np.float64)
test_smooth = smooth_31day(test.reshape(366, 1, 1))[:, 0, 0]
print(f"Test smooth[0]: {test_smooth[0]}")
# Day 0 should be mean of days 0-15 (indices -15..0 wrap to 351-365) and 0-15
# Days (0-15) mod 366 to (0+15) mod 366 = 351..365, 0..15
# That's 31 days: 351,352,...,365,0,1,...,15
# Mean should be (351+352+...+365+0+1+...+15)/31
# = (sum(0..15) + sum(351..365)) / 31
# = (120 + (351+365)*15/2) / 31 = (120 + 5370) / 31 = 5490/31 = 177.09677...

expected = (sum(range(0,16)) + sum(range(351,366))) / 31
print(f"Expected: {expected}, Got: {test_smooth[0]}")

# Day 15 should be mean of days 0-30
expected_15 = sum(range(0,31)) / 31
print(f"Day 15: expected {expected_15}, got {test_smooth[15]}")

# Apply smoothing
start = time.time()
threshold_smooth = smooth_31day(threshold_raw)
climatology_smooth = smooth_31day(climatology_raw)
elapsed = time.time() - start
print(f"Smoothed in {elapsed:.1f}s")

# Save smoothed results
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed thresholds and climatologies")
print(f"Threshold smooth shape: {threshold_smooth.shape}")
print(f"Climatology smooth shape: {climatology_smooth.shape}")
