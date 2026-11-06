
import numpy as np

# Check SST values
sst_target = np.load('/tmp/sst_target.npy')
sst_baseline = np.load('/tmp/sst_baseline.npy')

# Get non-NaN values for some target days
for d in [0, 30, 60, 90]:
    vals = sst_target[d][~np.isnan(sst_target[d])]
    if len(vals) > 0:
        print(f"Day {d}: min={vals.min():.2f}, max={vals.max():.2f}, mean={vals.mean():.2f}")

# Baseline values for June
print("\nBaseline June values:")
# Find June dates in baseline
baseline_dates = np.load('/tmp/baseline_dates.npy')
import pandas as pd
june_mask = np.array([pd.Timestamp(d).month == 6 for d in baseline_dates])
vals = sst_baseline[june_mask]
vals = vals[~np.isnan(vals)]
print(f"  min={vals.min():.2f}, max={vals.max():.2f}, mean={vals.mean():.2f}")
