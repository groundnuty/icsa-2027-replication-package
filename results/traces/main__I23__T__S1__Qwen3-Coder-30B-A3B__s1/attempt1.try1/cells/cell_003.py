import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'

# Open the file to examine its structure
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", ds.dims)
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    if 'sst' in ds.data_vars:
        print("SST shape:", ds.sst.shape)
        print("SST coordinates:", ds.sst.coords)
        print("SST first few values:")
        print(ds.sst.isel(time=0, lat=0, lon=0))