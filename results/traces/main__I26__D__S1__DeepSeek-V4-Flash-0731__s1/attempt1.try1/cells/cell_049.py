import numpy as np

# Test the joining logic
def detect_cell_mhw(hot_cell):
    n = len(hot_cell)
    runs = []
    in_run = False
    for i in range(n):
        if hot_cell[i]:
            if not in_run:
                run_start = i
                in_run = True
        else:
            if in_run:
                runs.append((run_start, i - 1))
                in_run = False
    if in_run:
        runs.append((run_start, n - 1))
    
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if len(mhws) <= 1:
        joined = mhws
    else:
        joined = [mhws[0]]
        for i in range(1, len(mhws)):
            prev_s, prev_e = joined[-1]
            curr_s, curr_e = mhws[i]
            gap = curr_s - prev_e - 1
            if gap <= 2:
                joined[-1] = (prev_s, curr_e)
            else:
                joined.append((curr_s, curr_e))
    
    mask = np.zeros(n, dtype=bool)
    for s, e in joined:
        mask[s:e+1] = True
    return mask

# Test case 1: Two runs separated by 1 day
hot1 = np.zeros(20, dtype=bool)
hot1[1:6] = True  # days 1-5
hot1[7:12] = True # days 7-11 (1 gap at day 6)
mask1 = detect_cell_mhw(hot1)
print("Test 1 (1-day gap):", np.where(mask1)[0])  # Should be days 1-11
assert np.all(mask1[1:12] == True)

# Test case 2: Two runs separated by 2 days
hot2 = np.zeros(20, dtype=bool)
hot2[1:6] = True  # days 1-5
hot2[8:13] = True # days 8-12 (gap at days 6-7)
mask2 = detect_cell_mhw(hot2)
print("Test 2 (2-day gap):", np.where(mask2)[0])  # Should be days 1-12
assert np.all(mask2[1:13] == True)

# Test case 3: Two runs separated by 3 days (should NOT join)
hot3 = np.zeros(20, dtype=bool)
hot3[1:6] = True  # days 1-5
hot3[9:14] = True # days 9-13 (gap at days 6-8)
mask3 = detect_cell_mhw(hot3)
print("Test 3 (3-day gap):", np.where(mask3)[0])  # Should be days 1-5 and 9-13
assert np.all(mask3[1:6] == True)
assert np.all(mask3[9:14] == True)
assert not np.any(mask3[6:9])

# Test case 4: Single run of exactly 5 days
hot4 = np.zeros(20, dtype=bool)
hot4[3:8] = True  # days 3-7
mask4 = detect_cell_mhw(hot4)
print("Test 4 (exactly 5 days):", np.where(mask4)[0])  # Should be days 3-7
assert np.all(mask4[3:8] == True)

# Test case 5: Single run of 4 days (should NOT be an MHW)
hot5 = np.zeros(20, dtype=bool)
hot5[3:7] = True  # days 3-6 (4 days)
mask5 = detect_cell_mhw(hot5)
print("Test 5 (4 days):", np.where(mask5)[0])  # Should be empty
assert not np.any(mask5)

# Test case 6: Three runs, where joining cascades
hot6 = np.zeros(30, dtype=bool)
hot6[1:6] = True   # days 1-5
hot6[8:13] = True  # days 8-12 (gap of 2 at days 6-7)
hot6[15:20] = True # days 15-19 (gap of 2 at days 13-14)
mask6 = detect_cell_mhw(hot6)
print("Test 6 (cascade join):", np.where(mask6)[0])  # Should be days 1-19
assert np.all(mask6[1:20] == True)

print("\nAll joining tests passed!")
