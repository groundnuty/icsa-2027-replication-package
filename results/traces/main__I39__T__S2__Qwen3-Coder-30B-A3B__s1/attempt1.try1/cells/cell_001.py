import fsspec
import xarray as xr

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Try to open the dataset
try:
    with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print("Dataset dimensions:", ds.dims)
        print("Dataset variables:", list(ds.data_vars.keys()))
        print("Coordinates:")
        for coord in ds.coords:
            print(f"  {coord}: {ds[coord].shape}")
        print("\nFirst few values of lat:", ds['lat'].values[:5])
        print("First few values of lon:", ds['lon'].values[:5])
        print("First few values of time:", ds['time'].values[:5])
        print("\nSST variable info:")
        print(ds['sst'])
except Exception as e:
    print(f"Error opening dataset: {e}")