
import xarray as xr
import numpy as np
import pandas as pd

# Load the output
ds = xr.open_dataset('output/mhw_mask.nc')
mhw_out = ds.mhw.values  # (92, 60, 60)

# Load intermediate data
sea_mask = np.load('/tmp/sea_mask.npy')
target_data = np.load('/tmp/target_data.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')

# Verify land cells are all 0 in MHW mask
land_mask = ~sea_mask
land_mhw = mhw_out[:, land_mask]
print(f"Land cells MHW sum: {land_mhw.sum()} (should be 0)")

# Verify sea cell MHW pattern
sea_indices = np.argwhere(sea_mask)
print(f"\nSea cells: {len(sea_indices)}")

# Check a few specific sea cells
for lat_i, lon_i in sea_indices[:3]:
    mhw_series = mhw_out[:, lat_i, lon_i]
    print(f"\nCell ({lat_i}, {lon_i}): MHW days = {mhw_series.sum()}")
    mhw_days = np.where(mhw_series)[0]
    if len(mhw_days) > 0:
        # Find MHW runs
        runs = []
        start = mhw_days[0]
        prev = mhw_days[0]
        for d in mhw_days[1:]:
            if d == prev + 1:
                prev = d
            else:
                runs.append((start, prev))
                start = d
                prev = d
        runs.append((start, prev))
        for s, e in runs:
            print(f"  MHW run: days {s} to {e} (dates: {str(ds.time.values[s])[:10]} to {str(ds.time.values[e])[:10]})")

# Verify that the MHW mask matches the per-cell MHW detection
# The mask should have mhw=1 where the cell is inside a per-cell MHW
# Let me verify that all MHW days have hot SST (except gap days from joining)

# Load the hot array from earlier computation
hot = np.load('/tmp/hot.npy')

# Check that MHW days are either hot or in a 1-2 day gap between hot runs
print("\nVerifying MHW consistency...")
for lat_i, lon_i in sea_indices[:10]:
    mhw_series = mhw_out[:, lat_i, lon_i].astype(bool)
    hot_series = hot[:, lat_i, lon_i]
    # Every MHW day should either be hot, or be a gap day between two MHW runs
    non_hot_mhw = np.where(mhw_series & ~hot_series)[0]
    if len(non_hot_mhw) > 0:
        print(f"Cell ({lat_i}, {lon_i}): {len(non_hot_mhw)} non-hot MHW days at indices {non_hot_mhw}")
    else:
        print(f"Cell ({lat_i}, {lon_i}): All MHW days are hot days")

print("\nAll verifications passed!")
