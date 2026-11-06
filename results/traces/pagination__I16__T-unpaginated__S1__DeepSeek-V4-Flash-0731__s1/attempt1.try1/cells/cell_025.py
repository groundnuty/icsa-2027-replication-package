
import numpy as np

# Check target data values
target_data = np.load('/tmp/target_data.npy')
valid = target_data[~np.isnan(target_data)]
print('Target SST range:', valid.min(), valid.max())
print('Target SST mean:', valid.mean())

# Check baseline data values
baseline_data = np.load('/tmp/baseline_data.npy')
valid_b = baseline_data[~np.isnan(baseline_data)]
print('Baseline SST range:', valid_b.min(), valid_b.max())
print('Baseline SST mean:', valid_b.mean())
