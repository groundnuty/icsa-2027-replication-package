
import numpy as np

# Verify with test array
test = np.arange(366.0)

def smooth_wrap_correct(arr):
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    result = np.zeros_like(arr)
    for i in range(366):
        result[i] = np.mean(padded[i:i+31], axis=0)
    return result

smoothed_correct = smooth_wrap_correct(test)

# Check index 0: should average indices 351-365 and 0-15
expected_0 = np.mean(np.concatenate([test[351:366], test[0:16]]))
print("Index 0:", smoothed_correct[0], "Expected:", expected_0)

# Check index 15: should average indices 0-30
expected_15 = np.mean(test[0:31])
print("Index 15:", smoothed_correct[15], "Expected:", expected_15)

# Check index 350: should average indices 335-365
expected_350 = np.mean(test[335:366])
print("Index 350:", smoothed_correct[350], "Expected:", expected_350)

# Check index 365: should average indices 350-365 and 0-14
expected_365 = np.mean(np.concatenate([test[350:366], test[0:15]]))
print("Index 365:", smoothed_correct[365], "Expected:", expected_365)
