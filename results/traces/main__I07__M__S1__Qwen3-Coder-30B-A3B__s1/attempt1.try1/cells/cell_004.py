import xarray as xr
import os

# Check the first few files to understand the structure
path_s1z = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(path_s1z))[:5]  # Get first 5 files

print("Sample files:")
for f in files:
    print(f)

# Load one file to see its structure
sample_file = os.path.join(path_s1z, files[0])
print(f"\nLoading sample file: {sample_file}")
try:
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Dataset coordinates and variables:")
    print(ds.coords)
    print(ds.data_vars)
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")