
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')

li, loni = 30, 30

# Check with full precision
for doy in [59, 60, 61]:
    print(f"Day {doy}: threshold={threshold_raw[doy-1, li, loni]:.10f}, climatology={climatology_raw[doy-1, li, loni]:.10f}")

# Check day 60 = mean of 59 and 61
print(f"\nDay 59 threshold: {threshold_raw[58, li, loni]:.10f}")
print(f"Day 61 threshold: {threshold_raw[60, li, loni]:.10f}")
print(f"Mean: {(threshold_raw[58, li, loni] + threshold_raw[60, li, loni])/2:.10f}")
print(f"Day 60 threshold: {threshold_raw[59, li, loni]:.10f}")
