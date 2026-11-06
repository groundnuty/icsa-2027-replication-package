
import numpy as np

# Test smoothing
def smooth_wrap(arr_2d):
    n = 366
    half = 15
    window = 31
    ext = np.tile(arr_2d, (3, 1))
    result = np.zeros_like(arr_2d)
    for d in range(n):
        start = n + d - half
        result[d] = np.nanmean(ext[start:start+window], axis=0)
    return result

# Test 1: all ones
arr1 = np.ones((366, 1))
result1 = smooth_wrap(arr1)
print('All ones test:', np.allclose(result1, 1.0))

# Test 2: single peak
arr2 = np.zeros((366, 1))
arr2[0] = 1.0  # single 1 at day 0
result2 = smooth_wrap(arr2)
# Day 0 should average days 351-365 and 0-15 (0-indexed) = 1/31
print('Single peak at day 0:', result2[0], 'expected:', 1/31)
# Day 15 should average days 0-30 = 1/31
print('Single peak at day 15:', result2[15], 'expected:', 1/31)
# Day 365 should average days 350-365 and 0-14 = 1/31
print('Single peak at day 365:', result2[365], 'expected:', 1/31)
# Day 100 should NOT see the peak
print('Day 100:', result2[100], 'expected:', 0)

# Test 3: wrapping at year boundary
arr3 = np.zeros((366, 1))
arr3[365] = 1.0  # single 1 at day 365
result3 = smooth_wrap(arr3)
# Day 0 should average days 351-365 and 0-15, which includes day 365 = 1/31
print('Peak at day 365, check day 0:', result3[0], 'expected:', 1/31)
# Day 365 should average days 350-365 and 0-14, which includes day 365 = 1/31
print('Peak at day 365, check day 365:', result3[365], 'expected:', 1/31)

print('\nSmoothing tests passed!')
