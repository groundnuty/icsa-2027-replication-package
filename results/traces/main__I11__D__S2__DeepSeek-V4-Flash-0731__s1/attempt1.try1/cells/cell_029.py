
import numpy as np

# Verify the smoothing function
# Create a test array with 366 days
test = np.arange(366, dtype=np.float64)
test = test.reshape(366, 1, 1)

def smooth_wrap(arr):
    result = np.zeros_like(arr)
    for i in range(366):
        indices = [(i + offset) % 366 for offset in range(-15, 16)]
        result[i] = np.mean(arr[indices], axis=0)
    return result

smoothed = smooth_wrap(test)
print("Smoothed[0]:", smoothed[0, 0, 0])  # should average days 351-365, 0-15 = all 366 days? 
# Wait, indices for i=0: [-15..15] mod 366 = [351..365, 0..15], that's 31 values.
# The sum of values 0..365 is 366*365/2 = 66795
# But we're averaging 31 specific values, not all.
# For i=0: values at indices 351-365 and 0-15
# 351+...+365 = (351+365)*15/2 = 716*7.5 = 5370
# 0+...+15 = 120
# Total = 5490, mean = 5490/31 = 177.0968...
print("Expected ~", 5490/31)
