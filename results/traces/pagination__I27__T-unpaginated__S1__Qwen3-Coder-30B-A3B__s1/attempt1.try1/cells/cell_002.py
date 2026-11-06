import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
# Let's examine a sample file to understand the structure
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(sample_file, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", ds.dims)
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    if 'sst' in ds.data_vars:
        print("SST shape:", ds.sst.shape)
        print("SST coordinates:", ds.sst.coords)
    ds.close()