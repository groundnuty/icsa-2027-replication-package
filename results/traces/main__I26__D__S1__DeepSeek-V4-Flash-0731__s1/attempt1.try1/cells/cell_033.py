import numpy as np

def smooth_366(arr):
    """arr: (..., 366), smooth along last axis with 31-day wrap-around window."""
    n = 366
    half = 15
    
    # Pad: prepend last 15, append first 15
    pad = np.concatenate([arr[..., -half:], arr, arr[..., :half]], axis=-1)  # length 396
    
    # Cumulative sum with zero prefix
    # csum[k] = sum(pad[:k]) for k=0..396
    csum = np.concatenate([np.zeros(arr.shape[:-1] + (1,)), np.cumsum(pad, axis=-1)], axis=-1)
    # csum has length 397
    # For day d (0-indexed in original), window is pad[d:d+31]
    # sum = csum[d+31] - csum[d]
    
    window_sum = csum[..., 31:] - csum[..., :-31]  # length 397 - 31 = 366
    
    result = window_sum / 31.0
    return result

# Test
test2 = np.zeros((1, 1, 366))
test2[0, 0, 0] = 1.0
result2 = smooth_366(test2)
print("Result shape:", result2.shape)
print(f"Day 0 (should be 1/31): {result2[0,0,0]:.6f}")
print(f"Day 15 (should be 1/31): {result2[0,0,15]:.6f}")
print(f"Day 16 (should be 0): {result2[0,0,16]:.6f}")
print(f"Day 350 (should be 1/31): {result2[0,0,350]:.6f}")
print(f"Day 351 (should be 1/31): {result2[0,0,351]:.6f}")

# Also test with all ones - should give 1
test3 = np.ones((1, 1, 366))
result3 = smooth_366(test3)
print(f"All ones, day 0: {result3[0,0,0]:.6f}")
print(f"All ones, day 100: {result3[0,0,100]:.6f}")
