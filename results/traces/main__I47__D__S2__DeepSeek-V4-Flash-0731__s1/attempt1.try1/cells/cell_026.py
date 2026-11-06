
import numpy as np
import pickle

# Load pool data for a specific cell and day
base_data = np.load('/work/base_data.npy').astype(np.float64)
with open('/work/pool_dates.pkl', 'rb') as f:
    pool_dates = pickle.load(f)

# Check cell (0,0), day 153 (Jun 1)
d = 153
idx = np.array(pool_dates[d])
pool = base_data[idx, 0, 0]

# Remove NaN
pool_valid = pool[~np.isnan(pool)]
n = len(pool_valid)
print(f"Pool size for cell (0,0), day {d}: {n}")

# numpy hazen
th_numpy = np.percentile(pool_valid, 90, method='hazen')
print(f"numpy hazen: {th_numpy}")

# Manual MATLAB-style (linear interpolation at position (n-1)*p+1)
sorted_pool = np.sort(pool_valid)
pos = (n-1) * 0.9 + 1  # 1-indexed position
k = int(np.floor(pos))
frac = pos - k
if k < n:
    th_manual = sorted_pool[k-1] + (sorted_pool[k] - sorted_pool[k-1]) * frac
else:
    th_manual = sorted_pool[k-1]
print(f"Manual MATLAB-style: {th_manual}")

print(f"Match: {np.isclose(th_numpy, th_manual)}")
