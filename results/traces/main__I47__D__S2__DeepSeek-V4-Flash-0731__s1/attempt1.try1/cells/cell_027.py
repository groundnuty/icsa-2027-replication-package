
import xarray as xr
import numpy as np

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values

# Check day 10 (index 9, 2019-06-10) - should be in first event
print("Day 10 (2019-06-10) mhw sum:", mhw[9].sum())

# Check day 30 (index 29, 2019-06-30) - should NOT be active (outside events)
print("Day 30 (2019-06-30) mhw sum:", mhw[29].sum())

# Check day 55 (index 54, 2019-07-25) - should be in second event
print("Day 55 (2019-07-25) mhw sum:", mhw[54].sum())

# Check day 5 (index 4, 2019-06-05) - should NOT be active
print("Day 5 (2019-06-05) mhw sum:", mhw[4].sum())

# Check day 23 (index 22, 2019-06-23) - should NOT be active (first event ends Jun 22)
print("Day 23 (2019-06-23) mhw sum:", mhw[22].sum())

# Check day 49 (index 48, 2019-07-19) - should NOT be active
print("Day 49 (2019-07-19) mhw sum:", mhw[48].sum())

# Verify total non-zero entries
print("\nTotal mhw=1 entries:", mhw.sum())

# Verify per-cell MHW durations by checking specific cells
# Find cells that were active during the first event (day 6-22)
active_first = mhw[5:22].sum(axis=(1,2))  # sum over cells for each day
print("\nActive cells per day (first event):")
for i in range(17):
    d = i + 6
    if active_first[i] > 0:
        print(f"  Day {d}: {active_first[i]} cells")
