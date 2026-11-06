import numpy as np

# Load target data
target_data = np.load('/work/target_data.npy').astype(np.float64)

# Check value ranges
valid = target_data[~np.isnan(target_data)]
print(f"Target SST range: {valid.min():.2f} to {valid.max():.2f}")
print(f"Target SST mean: {valid.mean():.2f}")
print(f"Some sample values: {valid[:10]}")

# Check baseline data range
baseline_data = np.load('/work/baseline_data.npy').astype(np.float64)
valid_base = baseline_data[~np.isnan(baseline_data)]
print(f"Baseline SST range: {valid_base.min():.2f} to {valid_base.max():.2f}")
print(f"Baseline SST mean: {valid_base.mean():.2f}")

# Check the threshold values
threshold_smooth = np.load('/work/threshold_smooth.npy')
print(f"Threshold range: {threshold_smooth.min():.2f} to {threshold_smooth.max():.2f}")

# Check a specific cell and day
# Let's look at cell (0, 0) for DOY 153 (June 1)
print(f"Cell (0,0) target SST on day 0 (Jun 1): {target_data[0, 0, 0]}")
print(f"Cell (0,0) threshold for DOY 153: {threshold_smooth[0, 0, 152]}")
