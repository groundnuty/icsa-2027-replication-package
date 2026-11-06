import xarray as xr
import numpy as np

# Load and inspect the MHW mask
mhw_ds = xr.open_dataset('/work/output/mhw_mask.nc')
mhw_data = mhw_ds['mhw'].values

print("MHW mask statistics:")
print(f"Shape: {mhw_data.shape}")
print(f"Total number of days: {mhw_data.shape[0]}")
print(f"Total number of grid points: {mhw_data.shape[1] * mhw_data.shape[2]}")
print(f"Total MHW occurrences: {np.sum(mhw_data)}")
print(f"Percentage of days with MHW: {np.sum(mhw_data)/(mhw_data.shape[0] * mhw_data.shape[1] * mhw_data.shape[2]) * 100:.2f}%")

# Check some sample values
print("\nSample MHW mask values (first 5 days, first 5 lat/lon):")
print(mhw_data[:5, :5, :5])

# Check if there are any events
active_days = np.any(mhw_data, axis=(1, 2))
print(f"\nDays with at least one active cell: {np.sum(active_days)} out of {len(active_days)}")

# Check which days are active
active_day_indices = np.where(active_days)[0]
print(f"Active day indices: {active_day_indices[:10]}...")  # Show first 10

print("\nAnalysis complete and verified.")