
import numpy as np
from datetime import date, timedelta

hot = np.load('/tmp/hot.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')

# Check cell 2805
c = 2805
print(f'Cell {c} hot pattern (92 days):')
print(hot[:, c])
print(f'MHW mask (92 days):')
print(mhw_mask[:, c])
print()

# Find runs of hot days
hot_series = hot[:, c].astype(bool)
runs = []
i = 0
while i < len(hot_series):
    if hot_series[i]:
        start = i
        while i < len(hot_series) and hot_series[i]:
            i += 1
        end = i - 1
        runs.append((start, end))
    else:
        i += 1
print('Runs of hot days:', runs)
runs_5 = [r for r in runs if r[1] - r[0] + 1 >= 5]
print('Runs >= 5:', runs_5)
