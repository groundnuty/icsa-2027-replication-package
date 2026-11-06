import xarray as xr
import numpy as np

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Extract the region of interest
region_ds = ds.sel(latitude=slice(57.33, 58.53), longitude=slice(9.03, 10.23))

# Extract the time period of interest (2012-06-01 to 2012-08-31)
region_ds = region_ds.sel(time=slice('2012-06-01', '2012-08-31'))

print("Region subset dimensions:", region_ds.dims)
print("Region subset shape:", region_ds.analysed_sst.shape)
print("Time range in subset:", region_ds.time.min().values, "to", region_ds.time.max().values)

# Check how many valid (finite) days per grid point
print("\nChecking for valid data points...")
valid_days_per_cell = np.sum(np.isfinite(region_ds.analysed_sst.values), axis=0)
print("Valid days per cell min/max:", valid_days_per_cell.min(), "/", valid_days_per_cell.max())

# Identify sea cells (cells with finite SST on every day)
sea_cells = np.all(np.isfinite(region_ds.analysed_sst.values), axis=0)
print("Number of sea cells (all finite on all days):", np.sum(sea_cells))

ds.close()