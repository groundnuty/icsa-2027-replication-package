
# Verify the circular moving mean implementation
import numpy as np

# Test with a simple array
arr = np.array([[1., 2., 3., 4., 5.]])
window = 3  # day d averages days d-1, d, d+1

# My implementation
def circular_moving_mean(arr, window=31):
    n = arr.shape[-1]
    half = window // 2
    kernel = np.ones(window) / window
    result = np.empty_like(arr, dtype=np.float64)
    for i in range(arr.shape[0]):
        padded = np.concatenate([arr[i, -half:], arr[i], arr[i, :half]])
        result[i] = np.convolve(padded, kernel, mode='valid')
    return result

# For window=3, half=1
# arr[0] = [1,2,3,4,5]
# padded = [5, 1,2,3,4,5, 1]
# kernel = [1/3, 1/3, 1/3]
# result[0] = convolution of [5,1,2,3,4,5,1] with [1/3,1/3,1/3] mode='valid'
# = [ (5+1+2)/3, (1+2+3)/3, (2+3+4)/3, (3+4+5)/3, (4+5+1)/3 ]
# = [8/3, 2, 3, 4, 10/3]

result = circular_moving_mean(arr, 3)
print("Result:", result)

# Manual check
# Day 0: average of day 4 (wrap) + day 0 + day 1 = (5+1+2)/3 = 8/3
# Day 1: (1+2+3)/3 = 2
# Day 2: (2+3+4)/3 = 3
# Day 3: (3+4+5)/3 = 4
# Day 4: (4+5+1)/3 = 10/3
print("Expected: [2.667, 2, 3, 4, 3.333]")
print("Got:      ", result[0])
