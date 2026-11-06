import xarray as xr
import fsspec

# First, let's download and examine one file to understand the structure
fs = fsspec.filesystem('onedata')
remote_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = '/work/sst_19820101.nc'

fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset dimensions:", ds.dims)
print("Dataset variables:", list(ds.data_vars.keys()))
print("Coordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds.coords[coord].shape}")
    
# Check the SST data specifically
if 'sst' in ds.data_vars:
    print("\nSST variable details:")
    print(ds.sst)
    print("SST shape:", ds.sst.shape)
    print("SST coordinates:", ds.sst.coords)
    
ds.close()