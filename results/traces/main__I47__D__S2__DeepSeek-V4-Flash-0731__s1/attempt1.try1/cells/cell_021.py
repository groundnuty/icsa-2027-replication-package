
import numpy as np

# Compare the two algorithms
hot = np.load('/work/hot.npy')

def find_mhws_total_gap(hot_mask):
    """Original: gap = total days between runs"""
    T = len(hot_mask)
    runs = []
    i = 0
    while i < T:
        if hot_mask[i]:
            start = i
            while i < T and hot_mask[i]:
                i += 1
            runs.append((start, i-1))
        else:
            i += 1
    qualified = [r for r in runs if r[1]-r[0]+1 >= 5]
    if not qualified:
        return []
    merged = [qualified[0]]
    for run in qualified[1:]:
        prev = merged[-1]
        gap = run[0] - prev[1] - 1
        if 1 <= gap <= 2:
            merged[-1] = (prev[0], run[1])
        else:
            merged.append(run)
    return merged

def find_mhws_nonhot(hot_mask):
    """Updated: gap = count of non-hot days between runs"""
    T = len(hot_mask)
    runs = []
    i = 0
    while i < T:
        if hot_mask[i]:
            start = i
            while i < T and hot_mask[i]:
                i += 1
            runs.append((start, i-1))
        else:
            i += 1
    qualified = [r for r in runs if r[1]-r[0]+1 >= 5]
    if not qualified:
        return []
    merged = [qualified[0]]
    for run in qualified[1:]:
        prev = merged[-1]
        gap_days = range(prev[1]+1, run[0])
        non_hot_count = sum(not hot_mask[t] for t in gap_days)
        if 1 <= non_hot_count <= 2:
            merged[-1] = (prev[0], run[1])
        else:
            merged.append(run)
    return merged

# Check all cells for differences
diff_count = 0
for i in range(60):
    for j in range(60):
        r1 = find_mhws_total_gap(hot[:, i, j])
        r2 = find_mhws_nonhot(hot[:, i, j])
        if r1 != r2:
            diff_count += 1
            if diff_count <= 5:
                print(f"Diff at cell ({i},{j}):")
                print(f"  Total gap: {r1}")
                print(f"  Non-hot:   {r2}")

print(f"\nTotal cells with differences: {diff_count}")
