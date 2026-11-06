
import numpy as np

def find_per_cell_mhw(hot_array):
    """
    hot_array: boolean array over target days (1D)
    Returns a boolean array of same length indicating days in a per-cell MHW.
    """
    n = len(hot_array)
    in_mhw = np.zeros(n, dtype=bool)
    
    # Find maximal runs of consecutive hot days
    runs = []  # list of (start, end) inclusive
    i = 0
    while i < n:
        if hot_array[i]:
            start = i
            while i < n and hot_array[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    # Keep runs of length >= 5
    mhw_runs = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
    
    # Join runs separated by 1 or 2 non-hot days
    if not mhw_runs:
        return in_mhw
    
    joined = [mhw_runs[0]]
    for run in mhw_runs[1:]:
        prev_s, prev_e = joined[-1]
        s, e = run
        gap = s - prev_e - 1
        if 1 <= gap <= 2:
            # Join
            joined[-1] = (prev_s, e)
        else:
            joined.append(run)
    
    # Mark days in joined MHWs
    for s, e in joined:
        in_mhw[s:e+1] = True
    
    return in_mhw

# Test with simple example
hot_test = np.array([1,1,1,1,1,0,1,1,1,1,1,0,0,1,1,1,1,1])  # 5 hot, 1 cold, 5 hot, 2 cold, 5 hot
result = find_per_cell_mhw(hot_test.astype(bool))
print("Test:", result.astype(int))
# Expected: all days in MHW (gap of 1 and 2 both <= 2, so all joined)
print("Expected: [1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1]")

# Test with gap of 3
hot_test2 = np.array([1,1,1,1,1,0,0,0,1,1,1,1,1])
result2 = find_per_cell_mhw(hot_test2.astype(bool))
print("Test2:", result2.astype(int))
print("Expected: [1 1 1 1 1 0 0 0 1 1 1 1 1]")
