import xarray as xr
import fsspec
import numpy as np

# Download a few more files to check for valid data
fs = fsspec.filesystem('onedata')

# Let's look at a few more recent files to see if they have data
files_to_check = [
    '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_19900101.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_20100101.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_20160601.nc'
]

for i, remote_path in enumerate(files_to_check):
    local_path = f'/work/sst_{i+1}.nc'
    try:
        fs.get(remote_path, local_path)
        ds = xr.open_dataset(local_path, engine='h5netcdf')
        
        # Check if there are any valid (non-NaN) SST values
        sst_values = ds.analysed_sst.values.flatten()
        valid_count = np.sum(np.isfinite(sst_values))
        
        print(f"File {i+1} ({remote_path.split('/')[-1]}):")
        print(f"  Shape: {ds.analysed_sst.shape}")
        print(f"  Valid SST values: {valid_count}")
        print(f"  Min valid SST: {np.nanmin(sst_values) if valid_count > 0 else 'N/A'}")
        print(f"  Max valid SST: {np.nanmax(sst_values) if valid_count > 0 else 'N/A'}")
        print()
        
        ds.close()
    except Exception as e:
        print(f"Error reading {remote_path}: {e}")