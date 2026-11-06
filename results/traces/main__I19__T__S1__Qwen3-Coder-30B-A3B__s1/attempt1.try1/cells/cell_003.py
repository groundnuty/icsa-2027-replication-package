import xarray as xr
import fsspec

# Let's look at the structure of one file
fs = fsspec.filesystem('onedata')
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nLatitude coordinate name:", [k for k in ds.coords.keys() if 'lat' in k.lower()])
    print("Longitude coordinate name:", [k for k in ds.coords.keys() if 'lon' in k.lower()])
    print("\nFirst few latitudes:", ds['latitude'].values[:5])  
    print("First few longitudes:", ds['longitude'].values[:5])