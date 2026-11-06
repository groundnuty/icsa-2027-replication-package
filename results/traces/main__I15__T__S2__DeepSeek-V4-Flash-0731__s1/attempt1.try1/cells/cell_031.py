
import numpy as np
import pickle

# Verify np.percentile with method='hazen'
# Test with a simple array
test_vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print('Test array:', test_vals)
print('numpy hazen 90th percentile:', np.percentile(test_vals, 90, method='hazen'))
print('numpy linear 90th percentile:', np.percentile(test_vals, 90))

# Verify with the actual data
sst_base = np.load('sst_base.npy')
with open('pools.pkl', 'rb') as f:
    pools = pickle.load(f)

# Check cell (30, 30) at DOY=153
idx = pools[153]
data = sst_base[idx, :, :].astype(np.float64)
vals = data[:, 30, 30]
valid = ~np.isnan(vals)
print(f'\nCell (30,30), DOY=153: {valid.sum()} valid values')
print(f'  Mean: {np.mean(vals[valid]):.6f}')
print(f'  90th percentile (hazen): {np.percentile(vals[valid], 90, method="hazen"):.6f}')

# Also check with a few more DOYs
for doy in [59, 60, 61, 100, 200, 244, 300, 366]:
    if doy == 60:
        continue
    idx = pools[doy]
    data = sst_base[idx, :, :].astype(np.float64)
    vals = data[:, 30, 30]
    valid = ~np.isnan(vals)
    p90 = np.percentile(vals[valid], 90, method='hazen') if valid.sum() > 0 else np.nan
    mean = np.mean(vals[valid]) if valid.sum() > 0 else np.nan
    print(f'DOY {doy}: mean={mean:.4f}, p90={p90:.4f}, n={valid.sum()}')
