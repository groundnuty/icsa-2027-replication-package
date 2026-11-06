
import numpy as np

threshold_smooth = np.load('threshold_smooth.npy')
climatology_smooth = np.load('climatology_smooth.npy')

# Check values for various day-of-year values
# Day 1 (Jan 1), day 80 (Mar 21), day 153 (Jun 1), day 180 (Jul 1), day 244 (Aug 31)
for doy in [1, 80, 153, 180, 244]:
    idx = doy - 1
    # Get a sea cell
    t = threshold_smooth[idx, 20, 30]
    c = climatology_smooth[idx, 20, 30]
    print(f"Day {doy}: threshold={t:.4f}, climatology={c:.4f}, diff={t-c:.4f}")

# Also check a non-sea cell for reference
print("\nLand cell (0, 0):")
for doy in [1, 80, 153, 180, 244]:
    idx = doy - 1
    t = threshold_smooth[idx, 0, 0]
    c = climatology_smooth[idx, 0, 0]
    print(f"Day {doy}: threshold={t:.4f}, climatology={c:.4f}")
