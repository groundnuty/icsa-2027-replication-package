
import xarray as xr
import numpy as np
import pandas as pd

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Region
lat_idx = slice(217, 277)
lon_idx = slice(421, 481)

# Target: 2007-06-01 to 2007-08-31
tgt_start_idx = 9282
tgt_end_idx = 9373

# Load target data
print("Loading target data...")
tgt_sub = ds.analysed_sst.isel(time=slice(tgt_start_idx, tgt_end_idx+1),
                                latitude=lat_idx, longitude=lon_idx)
tgt_data = tgt_sub.values
print(f"Target shape: {tgt_data.shape}, dtype: {tgt_data.dtype}")
print(f"NaN count in target: {np.isnan(tgt_data).sum()}")

# Check how many cells are finite for all target days (sea cells)
sea_cells = ~np.isnan(tgt_data).any(axis=0)
print(f"Sea cells count: {sea_cells.sum()} out of {60*60}")
print(f"NaN count per time step:")
for t in range(tgt_data.shape[0]):
    nan_count = np.isnan(tgt_data[t]).sum()
    if nan_count > 0:
        print(f"  t={t}: {nan_count} NaN")
