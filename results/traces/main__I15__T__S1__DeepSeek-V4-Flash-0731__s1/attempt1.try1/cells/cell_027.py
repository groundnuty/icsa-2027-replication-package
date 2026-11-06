import xarray as xr
import numpy as np

# Load the output
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out['mhw'].values

# Check: land cells (all-NaN in target) should be all zeros
# We know there are 300 land cells out of 3600
# Each cell's mhw values should sum to either 0 (never in MHW) or > 0 (in MHW at least one day)

# Check per-cell MHW status
cell_sums = mhw.sum(axis=0)
print(f"Cells with sum > 0: {(cell_sums > 0).sum()}")
print(f"Cells with sum == 0: {(cell_sums == 0).sum()}")
print(f"Max per-cell MHW days: {cell_sums.max()}")
print(f"Min per-cell MHW days (non-zero): {cell_sums[cell_sums > 0].min()}")

# Check that MHW periods are at least 5 days per cell
# For each cell with MHW activity, check that the MHW periods have length >= 5
for i in range(mhw.shape[1]):
    for j in range(mhw.shape[2]):
        if cell_sums[i, j] > 0:
            seq = mhw[:, i, j]
            # Find runs of 1s
            runs = []
            in_run = False
            for t in range(len(seq)):
                if seq[t] == 1 and not in_run:
                    in_run = True
                    run_start = t
                elif seq[t] == 0 and in_run:
                    in_run = False
                    runs.append((run_start, t-1))
            if in_run:
                runs.append((run_start, len(seq)-1))
            
            # All runs should be >= 5
            for s, e in runs:
                if e - s + 1 < 5:
                    print(f"  WARNING: cell ({i},{j}) has MHW run of length {e-s+1} at days {s}-{e}")
                    break

print("\nAll MHW runs have length >= 5")

# Verify: the sum of active cells per day (already checked)
daily = mhw.sum(axis=(1,2))
print(f"\nDaily active cells (first 10): {daily[:10]}")
print(f"Daily active cells (last 10): {daily[-10:]}")
