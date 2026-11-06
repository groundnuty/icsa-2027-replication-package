import xarray as xr
import numpy as np

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Print detailed information about the dataset
print("Dataset dimensions:", ds.dims)
print("Dataset coordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds.coords[coord].shape}")

print("\nDataset variables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].shape}")

print("\nSample coordinate values:")
print("Latitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
print("Time range:", ds.time.min().values, "to", ds.time.max().values)

# Check the analysed_sst variable
print("\nAnalysed SST variable info:")
print("Shape:", ds.analysed_sst.shape)
print("Sample values (first few):", ds.analysed_sst.isel(time=0, latitude=0, longitude=0).values)