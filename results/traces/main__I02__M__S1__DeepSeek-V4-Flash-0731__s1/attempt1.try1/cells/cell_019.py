
import numpy as np

threshold = np.load('/tmp/threshold_unsmoothed.npy')
climatology = np.load('/tmp/climatology_unsmoothed.npy')

print(f"Threshold NaN count: {np.isnan(threshold).sum()}")
print(f"Climatology NaN count: {np.isnan(climatology).sum()}")

# Check per-cell
for i in range(60):
    for j in range(60):
        if np.isnan(threshold[i,j,:]).any():
            print(f"Cell ({i},{j}) has NaN in threshold: {np.where(np.isnan(threshold[i,j,:]))[0]}")
            break
    else:
        continue
    break
