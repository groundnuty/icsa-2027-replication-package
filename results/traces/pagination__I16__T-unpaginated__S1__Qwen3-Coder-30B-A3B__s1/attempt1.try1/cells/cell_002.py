import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'

# Open a sample file to examine structure
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nSST variable shape:", ds['sst'].shape)
    print("SST variable dims:", ds['sst'].dims)
    print("Latitudes:", ds['latitude'][:5].values)  # First 5 latitudes
    print("Longitudes:", ds['longitude'][:5].values)  # First 5 longitudes