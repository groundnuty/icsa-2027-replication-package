
import xarray as xr
import numpy as np
from datetime import date, timedelta

# Verify the regional event by checking the active day pattern in the mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
time_vals = ds.time.values

# Check active days
active = mhw.any(axis=(1, 2))
print("Active days pattern (0=not active, 1=active):")
print(active.astype(int))

# Find active day indices
active_indices = np.where(active)[0]
if len(active_indices) > 0:
    print(f"\nActive day range: day {active_indices[0]} to day {active_indices[-1]}")
    print(f"Active date range: {time_vals[active_indices[0]]} to {time_vals[active_indices[-1]]}")
    print(f"First active date: {np.datetime_as_string(time_vals[active_indices[0]], unit='D')}")
    print(f"Last active date: {np.datetime_as_string(time_vals[active_indices[-1]], unit='D')}")
    
    # Verify continuity
    gaps = np.diff(active_indices)
    print(f"Gaps between consecutive active days: {np.unique(gaps)}")
    
    # Verify the event
    if len(active_indices) == active_indices[-1] - active_indices[0] + 1:
        print(f"\nSingle continuous event: {np.datetime_as_string(time_vals[active_indices[0]], unit='D')} to {np.datetime_as_string(time_vals[active_indices[-1]], unit='D')}")
    else:
        print("\nMultiple events detected!")

# Count cells in MHW per day
print("\nMHW cells per day (first 10 active days):")
for i in range(active_indices[0], min(active_indices[0]+10, len(active))):
    print(f"  Day {i} ({np.datetime_as_string(time_vals[i], unit='D')}): {mhw[i].sum()} cells")

ds.close()
