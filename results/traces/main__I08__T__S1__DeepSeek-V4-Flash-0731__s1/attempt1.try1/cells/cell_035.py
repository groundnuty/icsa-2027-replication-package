
import numpy as np

# Load the hot and mhw masks
hot = np.load('/tmp/hot.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
tgt_times = np.load('/tmp/tgt_times.npy')

# Find cells where runs were joined (i.e., a gap of 1-2 non-hot days between long runs)
sea_indices = np.where(sea_mask)
n_sea = len(sea_indices[0])

# Check a few cells to verify the joining logic
import random
random.seed(42)
sample_cells = random.sample(range(n_sea), min(20, n_sea))

for k in sample_cells:
    i, j = sea_indices[0][k], sea_indices[1][k]
    hot_cell = hot[:, i, j]
    
    # Find runs of hot days
    runs = []
    in_run = False
    for t in range(len(hot_cell)):
        if hot_cell[t]:
            if not in_run:
                run_start = t
                in_run = True
        else:
            if in_run:
                runs.append((run_start, t-1))
                in_run = False
    if in_run:
        runs.append((run_start, len(hot_cell)-1))
    
    # Long runs (>=5)
    long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    if len(long_runs) >= 2:
        # Check if any were joined
        for idx in range(len(long_runs)-1):
            gap = long_runs[idx+1][0] - long_runs[idx][1] - 1
            if 1 <= gap <= 2:
                # These should be joined
                joined = mhw_mask[long_runs[idx][0]:long_runs[idx+1][1]+1, i, j]
                if np.all(joined == 1):
                    print(f"Cell ({i},{j}): Runs {long_runs[idx]} and {long_runs[idx+1]} joined correctly (gap={gap})")
                else:
                    print(f"Cell ({i},{j}): Runs {long_runs[idx]} and {long_runs[idx+1]} NOT joined (gap={gap}) - ERROR!")
            elif gap > 2:
                # Check they're NOT joined
                # Check the gap days
                gap_days = mhw_mask[long_runs[idx][1]+1:long_runs[idx+1][0], i, j]
                if np.all(gap_days == 0):
                    pass  # Correctly not joined
                else:
                    print(f"Cell ({i},{j}): Runs {long_runs[idx]} and {long_runs[idx+1]} should NOT be joined (gap={gap}) but gap days have MHW=1 - ERROR!")
