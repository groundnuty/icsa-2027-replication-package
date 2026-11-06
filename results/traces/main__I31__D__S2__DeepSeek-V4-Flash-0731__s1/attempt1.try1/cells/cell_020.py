
import numpy as np
import pandas as pd

thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')

# Cell (0,0)
i, j = 0, 0

# Check thresholds around DOY 153 (June 1)
print("Smoothed thresholds for cell (0,0):")
for d in range(143, 165):
    print(f"  DOY={d}: threshold={thresholds_smooth[d-1, i, j]:.2f}, clim={climatology_smooth[d-1, i, j]:.2f}")

# Also check the unsmoothed (raw) values - need to recompute
# Actually, let me just check the smoothed values more broadly
print("\nSmoothed thresholds for cell (0,0) over the target range:")
for d in range(153, 245, 10):
    print(f"  DOY={d}: threshold={thresholds_smooth[d-1, i, j]:.2f}, clim={climatology_smooth[d-1, i, j]:.2f}")
