import xarray as xr
import numpy as np

# Open the dataset
file_path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(file_path, engine="h5netcdf")

print("Dataset info:")
print(f"Dimensions: {ds.dims}")
print(f"Coordinates: {list(ds.coords.keys())}")
print(f"Variables: {list(ds.data_vars.keys())}")

# Check the actual range of coordinates
print(f"\nLatitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
print(f"Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")

# Check time range
print(f"Time range: {ds.time.min().values} to {ds.time.max().values}")

# Look at the analysed_sst variable
print(f"\nAnalysed SST variable shape: {ds.analysed_sst.shape}")
print(f"Analysed SST dtype: {ds.analysed_sst.dtype}")

# Close the dataset
ds.close()