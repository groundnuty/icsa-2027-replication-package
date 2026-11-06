import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
# Open one file to understand the structure
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nSST variable details:")
    print(ds['sst'])