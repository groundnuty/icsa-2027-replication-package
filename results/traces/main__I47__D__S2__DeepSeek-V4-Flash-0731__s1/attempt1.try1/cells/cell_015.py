
import numpy as np

# Load the threshold and climatology arrays (need to recompute them)
import pickle

base_data = np.load('/work/base_data.npy')
with open('/work/pool_dates.pkl', 'rb') as f:
    pool_dates = pickle.load(f)

n_lat = base_data.shape[1]
n_lon = base_data.shape[2]

threshold = np.zeros((366, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((366, n_lat, n_lon), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    idx = np.array(pool_dates[d])
    pool = base_data[idx]
    threshold[d-1] = np.nanpercentile(pool, 90, method='hazen', axis=0)
    climatology[d-1] = np.nanmean(pool, axis=0)

threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

print("Threshold/climatology computed")

# Smoothing function: 31-day centred moving mean wrapping around
def smooth_wrap(arr):
    """arr: (366, n_lat, n_lon). Smooth over axis 0 with 31-day centred moving mean wrapping around."""
    n = arr.shape[0]
    # Pad: prepend last 15, append first 15
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)  # (396, ...)
    result = np.zeros_like(arr)
    for i in range(n):
        result[i] = np.nanmean(padded[i:i+31], axis=0)
    return result

threshold_sm = smooth_wrap(threshold)
climatology_sm = smooth_wrap(climatology)

print("Smoothed")
print("threshold_sm shape:", threshold_sm.shape)
print("climatology_sm shape:", climatology_sm.shape)

# Check for NaN in sea cells
tgt_data = np.load('/work/tgt_data.npy')
tgt_nan = np.isnan(tgt_data).any(axis=0)
sea_cells = ~tgt_nan
print("Sea cells with NaN in smoothed threshold:", np.isnan(threshold_sm[:, sea_cells]).sum())
print("Sea cells with NaN in smoothed climatology:", np.isnan(climatology_sm[:, sea_cells]).sum())

# Save
np.save('/work/threshold_sm.npy', threshold_sm)
np.save('/work/climatology_sm.npy', climatology_sm)
print("Saved smoothed arrays")
