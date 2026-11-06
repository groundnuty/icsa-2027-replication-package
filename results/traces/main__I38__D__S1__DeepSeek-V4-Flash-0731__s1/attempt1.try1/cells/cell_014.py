import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Read the full needed time range and region
# Baseline: indices 3647 to 7674 (1991-12-27 to 2003-01-05)
# Target: indices 7821 to 7912 (2003-06-01 to 2003-08-31)
# Total: indices 3647 to 7912

# But I can read them separately for clarity

# First read the region data for baseline period
baseline_data = ds.analysed_sst[3647:7675, 350:410, 413:473].values
print("Baseline data shape:", baseline_data.shape)
print("Baseline dtype:", baseline_data.dtype)
print("Baseline NaN count:", np.isnan(baseline_data).sum())
print("Baseline finite count:", np.isfinite(baseline_data).sum())
print("Baseline min:", np.nanmin(baseline_data))
print("Baseline max:", np.nanmax(baseline_data))
print("Baseline mean:", np.nanmean(baseline_data))

# Check if some cells are always NaN
cell_nan_count = np.isnan(baseline_data).sum(axis=0)
print("\nCell NaN counts - unique values:", np.unique(cell_nan_count)[:10], "...")
# Check for cells that are always NaN (land)
always_nan = np.all(np.isnan(baseline_data), axis=0)
print("Always-NaN cells:", always_nan.sum(), "out of", always_nan.size)
