import xarray as xr
import numpy as np
import os

# Load and examine the MHW mask
ds = xr.open_dataset('/work/output/mhw_mask.nc')
print("MHW mask shape:", ds.mhw.shape)
print("Time dimension:", ds.time.values[:5], "...", ds.time.values[-5:])  
print("Number of locations:", len(ds.location))

# Check some sample values
sample_times = [0, 10, 20, 30, 40, 50, 60, 70, 80, 89]  # First, middle, and last few days
sample_locations = [0, 100, 500, 1000, 2000, 3299]  # First, middle, and last few locations

print("\nSample MHW values (time, location):")
for t in sample_times:
    for l in sample_locations[:3]:  # Just first few locations for brevity
        if t < len(ds.time) and l < len(ds.location):
            val = ds.mhw.values[t, l]
            if val == 1:
                print(f"  Day {t} ({ds.time.values[t]}), Loc {l}: MHW detected")

# Count total MHW occurrences
total_mhw_days = np.sum(ds.mhw.values)
print(f"\nTotal MHW occurrences in the dataset: {total_mhw_days}")

# Check if any MHWs occurred during the July period (when we expect them)
july_days = [t for t, date in enumerate(ds.time.values) if '07' in date]
if july_days:
    july_mhw_count = np.sum(ds.mhw.values[np.array(july_days), :])
    print(f"MHW occurrences in July: {july_mhw_count}")

ds.close()