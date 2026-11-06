
import numpy as np

threshold_raw = np.load('cache/threshold_raw.npy')
threshold_sm = np.load('cache/threshold_smoothed.npy')

# Verify smoothing for doy 221 (index 220) at cell (53,40)
i, j = 53, 40
doy = 221
idx = doy - 1  # 220

# Expected: mean of days 221-15=206 to 221+15=236 (mod 366)
indices = [(idx - 15 + k) % 366 for k in range(31)]
expected = np.mean([threshold_raw[k, i, j] for k in indices])
print(f'Expected smoothed threshold at doy 221, cell ({i},{j}): {expected:.6f}')
print(f'Actual smoothed threshold: {threshold_sm[idx, i, j]:.6f}')

# Verify the wrapping around for doy 1
idx_1 = 0
indices_1 = [(idx_1 - 15 + k) % 366 for k in range(31)]
print(f'Indices for doy 1: {indices_1}')
expected_1 = np.mean([threshold_raw[k, i, j] for k in indices_1])
print(f'Expected smoothed threshold at doy 1: {expected_1:.6f}')
print(f'Actual: {threshold_sm[0, i, j]:.6f}')
