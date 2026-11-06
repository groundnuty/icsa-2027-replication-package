
import numpy as np

# Verify smoothing
threshold_smooth = np.load('/tmp/threshold_smooth.npy')

# Check day 153 (June 1, doy 153, index 152)
# Window should be indices 137-167 (doy 138-168)
print("Manual check for index 152 (doy 153):")
print("Mean of indices 137-167:", np.mean(threshold_smooth[137:168, 20, 20]))
# But wait, threshold_smooth is already smoothed. I should check the raw threshold.

# Let me re-derive the raw threshold to verify smoothing
# Actually, I saved the smoothed version. Let me reconstruct and check.

# Let me verify with a simple test
test = np.arange(366.0)
def smooth_wrap(arr):
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    result = np.zeros_like(arr)
    for i in range(366):
        result[i] = np.mean(padded[i:i+31], axis=0)
    return result

smoothed_test = smooth_wrap(test)
# Check index 0: average of indices 351-365, 0-15 = 16 values from end + 16 from start = 32 values, but wait
# padded[0:31] = arr[351:366] + arr[0:16] = 15 + 16 = 31 values
# So index 0 should average arr[351:366] (15 values) and arr[0:16] (16 values) = 31 values
print("Smoothed test[0]:", smoothed_test[0])
expected_0 = np.mean(np.concatenate([test[351:366], test[0:16]]))
print("Expected[0]:", expected_0)

# Check index 15: padded[15+15:15+15+31] = padded[30:61] = arr[15:31] + arr[0:15] + ... wait
# padded[30:61] = arr[15:46] which is indices 15-45 (31 values)
print("Smoothed test[15]:", smoothed_test[15])
expected_15 = np.mean(test[15:46])
print("Expected[15]:", expected_15)

# Check index 350: padded[350+15:350+15+31] = padded[365:396]
# padded[365] = arr[350], padded[365:396] = arr[350:366] + arr[0:15]
print("Smoothed test[350]:", smoothed_test[350])
expected_350 = np.mean(np.concatenate([test[350:366], test[0:15]]))
print("Expected[350]:", expected_350)
