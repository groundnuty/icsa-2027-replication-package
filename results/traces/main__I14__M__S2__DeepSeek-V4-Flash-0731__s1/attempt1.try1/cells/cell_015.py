
import numpy as np
import pandas as pd
import pickle

sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')

with open('/tmp/pools.pkl', 'rb') as f:
    pools = pickle.load(f)

# Compute threshold for doy 153, cell (0,0) manually
pool_153 = pools[153]
cell_vals = sst_data[pool_153, 0, 0]
valid = cell_vals[np.isfinite(cell_vals)]
print("Number of valid values:", len(valid))
print("Values:", valid)

# 90th percentile with method='hazen'
p90 = np.quantile(valid, 0.9, method='hazen')
mean = np.mean(valid)
print("P90:", p90)
print("Mean:", mean)

# Compare with the computed smoothed values
thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')
climatology_smoothed = np.load('/tmp/climatology_smoothed.npy')
print("Smoothed threshold at doy 153:", thresholds_smoothed[152, 0, 0])
print("Smoothed climatology at doy 153:", climatology_smoothed[152, 0, 0])

# The raw (unsmoothed) threshold at doy 153
thresholds = np.load('/tmp/thresholds.npy')
print("Raw threshold at doy 153:", thresholds[152, 0, 0])
