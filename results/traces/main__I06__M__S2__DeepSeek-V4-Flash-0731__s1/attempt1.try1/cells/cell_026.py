
import numpy as np
import pandas as pd

mhw_cell = np.load('/tmp/mhw_cell.npy')
target_dates = np.load('/tmp/target_dates.npy')

# Active days: any cell in MHW
active = mhw_cell.any(axis=(1, 2))  # (92,)
print("Active days:", np.where(active)[0])

# Find maximal runs of consecutive active days
runs = []
in_run = False
start = 0
for d in range(len(active)):
    if active[d] and not in_run:
        in_run = True
        start = d
    elif not active[d] and in_run:
        in_run = False
        runs.append((start, d - 1))
if in_run:
    runs.append((start, len(active) - 1))

print("Regional events:")
for s, e in runs:
    onset = pd.Timestamp(target_dates[s]).strftime('%Y-%m-%d')
    end = pd.Timestamp(target_dates[e]).strftime('%Y-%m-%d')
    print(f"  Onset: {onset}, End: {end}, Duration: {e - s + 1} days")
