
import numpy as np

hot = np.load('/tmp/hot.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')

# Cells hot on day 0
hot_day0 = np.where(hot[0])[0]
print(f'Cells hot on day 0 (June 1): {len(hot_day0)}')
if len(hot_day0) > 0:
    print(hot_day0[:20])

# Cells in MHW on day 0
mhw_day0 = np.where(mhw_mask[0] > 0)[0]
print(f'Cells in MHW on day 0: {len(mhw_day0)}')

# Check if any cell has hot run starting at day 0 that is >= 5 days
n_days = hot.shape[0]
for c in range(hot.shape[1]):
    if hot[0, c]:
        # Check if there's a run starting at 0 of length >= 5
        run_len = 1
        t = 1
        while t < n_days and hot[t, c]:
            run_len += 1
            t += 1
        if run_len >= 5:
            print(f'Cell {c}: run starting at day 0 with length {run_len}')
