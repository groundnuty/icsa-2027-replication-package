
import xarray as xr
import numpy as np

# Read the mask file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values

# For each day, count how many cells are in MHW
daily_count = mhw.sum(axis=(1,2))
print("Days with at least one cell in MHW:")
for i in range(len(daily_count)):
    if daily_count[i] > 0:
        print(f"  Day {i}: {str(ds.time.values[i])[:10]}, cells in MHW: {daily_count[i]}")

# Find active days
active_days = [i for i in range(len(daily_count)) if daily_count[i] > 0]
print(f"\nActive day count: {len(active_days)}")
if active_days:
    print(f"First active: {ds.time.values[active_days[0]]}, Last active: {ds.time.values[active_days[-1]]}")
    
# Check for gaps
gaps = []
for i in range(len(active_days)-1):
    if active_days[i+1] - active_days[i] > 1:
        gaps.append((active_days[i], active_days[i+1]))
print(f"Gaps in active days: {len(gaps)}")
for g in gaps:
    print(f"  Gap between day {g[0]} and day {g[1]}")
