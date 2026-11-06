
# Test find_mhw_runs with edge cases
def find_mhw_runs(hot_days):
    n = len(hot_days)
    runs = []
    i = 0
    while i < n:
        if hot_days[i]:
            start = i
            while i < n and hot_days[i]:
                i += 1
            end = i - 1
            runs.append([start, end])
        else:
            i += 1
    
    if len(runs) == 0:
        return []
    
    merged = [runs[0].copy()]
    for r in runs[1:]:
        prev = merged[-1]
        gap = r[0] - prev[1] - 1
        if 1 <= gap <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(r.copy())
    
    mhw_runs = [(s, e) for s, e in merged if (e - s + 1) >= 5]
    return mhw_runs

# Test 1: 5 consecutive hot days
hot = np.array([1,1,1,1,1,0,0,0,0,0])
print("Test 1:", find_mhw_runs(hot))  # [(0,4)]

# Test 2: 4 hot days, 1 gap, 4 hot days -> joined to 9 days >= 5
hot = np.array([1,1,1,1,0,1,1,1,1,0])
print("Test 2:", find_mhw_runs(hot))  # [(0,8)]

# Test 3: 3 hot days, 1 gap, 3 hot days -> joined to 7 days >= 5
hot = np.array([1,1,1,0,1,1,1,0,0,0])
print("Test 3:", find_mhw_runs(hot))  # [(0,6)]

# Test 4: 2 hot days, 1 gap, 2 hot days -> joined to 5 days >= 5
hot = np.array([1,1,0,1,1,0,0,0,0,0])
print("Test 4:", find_mhw_runs(hot))  # [(0,4)]

# Test 5: 2 hot days, 2 gaps, 2 hot days -> joined to 6 days >= 5
hot = np.array([1,1,0,0,1,1,0,0,0,0])
print("Test 5:", find_mhw_runs(hot))  # [(0,5)]

# Test 6: 3 hot days, 3 gaps, 3 hot days -> NOT joined, each run < 5, no MHW
hot = np.array([1,1,1,0,0,0,1,1,1,0])
print("Test 6:", find_mhw_runs(hot))  # []

# Test 7: 4 hot days, 2 gaps, 1 hot day -> joined to 7 days >= 5
hot = np.array([1,1,1,1,0,0,1,0,0,0])
print("Test 7:", find_mhw_runs(hot))  # [(0,6)]

# Test 8: runs with 2-day gap joined
hot = np.array([1,1,1,1,1,0,0,1,1,1,1,1])
print("Test 8:", find_mhw_runs(hot))  # [(0,10)]

# Test 9: 4 hot days, 2 gaps, 4 hot days -> joined to 10 >= 5
hot = np.array([1,1,1,1,0,0,1,1,1,1])
print("Test 9:", find_mhw_runs(hot))  # [(0,9)]

# Test 10: 1 hot, 1 gap, 4 hot -> joined to 6 >= 5
hot = np.array([1,0,1,1,1,1,0,0,0,0])
print("Test 10:", find_mhw_runs(hot))  # [(0,5)]

print("\nAll test cases look correct")
