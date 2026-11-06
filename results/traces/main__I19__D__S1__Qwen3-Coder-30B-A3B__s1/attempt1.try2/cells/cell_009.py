import fsspec
import xarray as xr

# Try to directly download and check one file
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')

print("First few files:")
for i, f in enumerate(files[:5]):
    print(f"{i}: {f}")

# Download and examine one file to verify the structure
sample_file = files[0]
print(f"\nExamining: {sample_file}")

# Download to local
local_path = '/tmp/test.nc'
fs.get(sample_file, local_path)

# Open and examine
try:
    ds = xr.open_dataset(local_path, engine='h5netcdf')
    print("Successfully opened file")
    print("Variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    print("SST shape:", ds['analysed_sst'].shape)
except Exception as e:
    print(f"Error opening file: {e}")