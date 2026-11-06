
import numpy as np
import pandas as pd

baseline_data = np.load('/tmp/baseline_data.npy').astype(np.float64)
target_data = np.load('/tmp/target_data.npy').astype(np.float64)
sea_mask = np.load('/tmp/sea_mask.npy')

n_lat, n_lon = sea_mask.shape

# Find sea cells with NaN threshold (from the check above)
# Let me recompute to find which cells have all-NaN in the check days
# I'll compute the unsmoothed threshold for one day and find NaN cells

# Actually let me just check: do the 307 cells have any valid baseline data at all?
# Count NaN in baseline for each sea cell
nan_count_baseline = np.zeros((n_lat, n_lon), dtype=int)
valid_count_baseline = np.zeros((n_lat, n_lon), dtype=int)
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j]:
            vals = baseline_data[:, i, j]
            nan_count_baseline[i, j] = np.isnan(vals).sum()
            valid_count_baseline[i, j] = (~np.isnan(vals)).sum()

# Find sea cells with 0 valid baseline values
zero_valid = np.where((valid_count_baseline == 0) & sea_mask)
print("Sea cells with 0 valid baseline values:", len(zero_valid[0]))
if len(zero_valid[0]) > 0:
    print("  Indices:", list(zip(zero_valid[0][:5], zero_valid[1][:5])))

# Find sea cells with some but few valid baseline values
low_valid = np.where((valid_count_baseline > 0) & (valid_count_baseline < 10) & sea_mask)
print("Sea cells with 1-9 valid baseline values:", len(low_valid[0]))

# Distribution of valid baseline counts
valid_counts = valid_count_baseline[sea_mask]
print("Valid baseline count stats: min={}, max={}, mean={:.1f}".format(
    valid_counts.min(), valid_counts.max(), valid_counts.mean()))
print("Histogram:", np.histogram(valid_counts, bins=10)[0])
