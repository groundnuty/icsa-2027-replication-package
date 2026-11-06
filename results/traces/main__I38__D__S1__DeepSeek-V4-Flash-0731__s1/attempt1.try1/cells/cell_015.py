import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Read target period data
target_data = ds.analysed_sst[7821:7913, 350:410, 413:473].values
print("Target data shape:", target_data.shape)
print("Target dtype:", target_data.dtype)
print("Target NaN count:", np.isnan(target_data).sum())
print("Target finite count:", np.isfinite(target_data).sum())

# Check cells that are always NaN in target
cell_nan_target = np.isnan(target_data).sum(axis=0)
always_nan_target = np.all(np.isnan(target_data), axis=0)
print("Always-NaN cells in target:", always_nan_target.sum(), "out of", always_nan_target.size)

# Check which cells are sea cells (finite on every day of target period)
sea_cells = np.all(np.isfinite(target_data), axis=0)
print("Sea cells:", sea_cells.sum(), "out of", sea_cells.size)

# Also check cells that have NaN in baseline but are sea cells in target
baseline_data = ds.analysed_sst[3647:7675, 350:410, 413:473].values
baseline_always_nan = np.all(np.isnan(baseline_data), axis=0)
print("Cells always NaN in baseline but sea cells in target:", np.sum(baseline_always_nan & sea_cells))
print("Cells sea cells in baseline but always NaN in target:", np.sum(~baseline_always_nan & ~sea_cells))
