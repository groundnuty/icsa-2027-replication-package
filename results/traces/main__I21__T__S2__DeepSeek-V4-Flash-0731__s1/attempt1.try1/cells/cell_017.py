
import numpy as np
import xarray as xr
import pandas as pd

baseline_data = xr.open_dataset('baseline_data.nc')
baseline_time = baseline_data.time.values

# Check if daily
diffs = np.diff(baseline_time.astype('datetime64[D]').astype(np.int64))
print("Time differences (in days):")
print(f"  Unique diffs: {np.unique(diffs)}")
print(f"  Min: {diffs.min()}, Max: {diffs.max()}")

# Check there are no gaps
if len(np.unique(diffs)) == 1 and np.unique(diffs)[0] == 1:
    print("Data is daily and contiguous ✓")
else:
    print("WARNING: Data may have gaps")
    # Find gaps
    gaps = np.where(diffs != 1)[0]
    if len(gaps) > 0:
        for g in gaps[:10]:
            print(f"  Gap at index {g}: {pd.Timestamp(baseline_time[g])} to {pd.Timestamp(baseline_time[g+1])}")
