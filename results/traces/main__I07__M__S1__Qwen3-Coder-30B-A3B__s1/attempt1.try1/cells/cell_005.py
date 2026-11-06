import xarray as xr
import os

# Look at a more recent file to verify structure
path_s1z = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(path_s1z))
recent_files = files[-5:]  # Get last 5 files

print("Recent files:")
for f in recent_files:
    print(f)

# Load one recent file to see its structure
sample_file = os.path.join(path_s1z, recent_files[0])
print(f"\nLoading recent sample file: {sample_file}")
try:
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Dataset coordinates and variables:")
    print("Coordinates:")
    for coord in ds.coords:
        print(f"  {coord}: {ds.coords[coord].shape}")
    print("Variables:")
    for var in ds.data_vars:
        print(f"  {var}: {ds.data_vars[var].shape}")
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")