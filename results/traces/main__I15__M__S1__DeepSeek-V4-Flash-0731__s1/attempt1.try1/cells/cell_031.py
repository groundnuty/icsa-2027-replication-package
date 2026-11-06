import numpy as np

# Verify the smoothing wrap-around
# Create a simple array to test
test = np.zeros((366, 1))
test[0, 0] = 1.0  # day 1 has value 1

# Apply smoothing
def smooth_wrap(arr, window=31):
    n = arr.shape[0]
    half = window // 2  # 15
    result = np.zeros_like(arr)
    for d in range(n):
        indices = [(d + offset) % n for offset in range(-half, half + 1)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

result = smooth_wrap(test)

# Day 1 (index 0) averages days -14 to 16 (mod 366) = days 352-16 (1-indexed)
# Since test[0] = 1 and test[1] through test[365] = 0
# Day 1 result should be 1/31
print(f"Day 1 result: {result[0, 0]}")
print(f"Expected: {1/31}")

# Day 15 (index 14) averages days 0-30 (indices 0 to 30)
# Only index 0 has value 1, so result = 1/31
print(f"Day 15 result: {result[14, 0]}")
print(f"Expected: {1/31}")

# Day 16 (index 15) averages indices 0 to 30, but index 0 is included
# Wait, day 16 (index 15) averages indices 0 to 30, which includes index 0
# So result = 1/31
print(f"Day 16 result: {result[15, 0]}")

# Day 352 (index 351) averages indices 336 to 366 mod 366
# 336+15=351, 351+15=366 mod 366 = 0
# So indices 336 to 365, and 0
# Only index 0 has value 1, so result = 1/31
print(f"Day 352 result: {result[351, 0]}")
print(f"Expected: {1/31}")

# Day 366 (index 365) averages indices 350 to 380 mod 366
# 350-365, 0-14
# Includes index 0, so result = 1/31
print(f"Day 366 result: {result[365, 0]}")
print(f"Expected: {1/31}")
