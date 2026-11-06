import fsspec
import xarray as xr

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Open the file
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    # Load the dataset
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Print basic info about the dataset
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nTime dimension:", ds.dims.get('time'))
    print("Latitude dimension:", ds.dims.get('lat'))
    print("Longitude dimension:", ds.dims.get('lon'))
    
    # Check the actual data range
    print("\nLat range:", ds.lat.min().values, "to", ds.lat.max().values)
    print("Lon range:", ds.lon.min().values, "to", ds.lon.max().values)
    print("Time range:", ds.time.min().values, "to", ds.time.max().values)