
import xarray as xr
import numpy as np

# Load the output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
time = ds.time.values

# Check some specific cells
# Cell (0,0) - first lat, first lon
print("Cell (0,0) mhw:", mhw[:, 0, 0])
print("Cell (0,0) sum:", np.sum(mhw[:, 0, 0]))

# Check if land cells are 0
# Find land cells from the original computation
# All cells should be either 0 or have MHW values

# Let's check the active days pattern
active_days = np.any(mhw > 0, axis=(1,2))
print("\nActive days pattern:")
for i, a in enumerate(active_days):
    if a:
        print(f"  Day {i}: {time[i]} active")

# Find cells that are never in MHW
never = np.all(mhw == 0, axis=0)
print("\nCells never in MHW:", np.sum(never), "out of", mhw.shape[1]*mhw.shape[2])

# Check the active days
print("\nTotal active days:", np.sum(active_days))
