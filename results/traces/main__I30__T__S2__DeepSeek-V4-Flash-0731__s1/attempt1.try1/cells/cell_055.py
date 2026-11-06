
import numpy as np
import pandas as pd

mhw_mask = np.load('/tmp/mhw_mask.npy')
hot = np.load('/tmp/hot.npy')
target_time = np.load('/tmp/target_time.npy')

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
n_time = len(target_dates)

# Cell (4, 10) with gap at index 40
lat_i, lon_j = 4, 10
h = hot[:, lat_i, lon_j]
m = mhw_mask[:, lat_i, lon_j]

print(f"Cell ({lat_i}, {lon_j}) hot and MHW pattern:")
for t in range(n_time):
    if h[t] or m[t]:
        marker = ""
        if h[t]:
            marker += "H"
        if m[t]:
            marker += "M"
        print(f"  idx {t:2d} {target_dates[t].strftime('%Y-%m-%d')}: {marker}")

# Verify the join logic
runs = []
i = 0
while i < len(h):
    if h[i]:
        start = i
        while i < len(h) and h[i]:
            i += 1
        end = i - 1
        runs.append((start, end))
    else:
        i += 1

print(f"\nHot runs: {runs}")
mhws = [(s, e) for s, e in runs if (e - s + 1) >= 5]
print(f"MHWs (runs >= 5): {mhws}")

joined = []
if mhws:
    current = list(mhws[0])
    for next_mhw in mhws[1:]:
        gap = next_mhw[0] - current[1] - 1
        print(f"  Gap between MHW {current} and {next_mhw}: {gap} days")
        if 1 <= gap <= 2:
            current[1] = next_mhw[1]
        else:
            joined.append(tuple(current))
            current = list(next_mhw)
    joined.append(tuple(current))
print(f"Joined MHWs: {joined}")

# Verify mhw_mask matches
expected_mhw = np.zeros(n_time, dtype=bool)
for s, e in joined:
    expected_mhw[s:e+1] = True
print(f"\nmhw_mask matches expected: {np.array_equal(m, expected_mhw)}")
