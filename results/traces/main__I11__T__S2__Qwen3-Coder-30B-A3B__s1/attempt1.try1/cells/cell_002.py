import fsspec
import xarray as xr

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", ds.dims)
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    
    # Check the actual data range
    print("\nLatitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
    print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
    print("Time range:", ds.time.min().values, "to", ds.time.max().values)
    
    # Check what we need for our region
    lat_min, lat_max = 55.67, 56.87
    lon_min, lon_max = 16.45, 17.65
    
    # Select our region
    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    print("\nSelected region dimensions:", region_ds.dims)
    print("Region latitude range:", region_ds.latitude.min().values, "to", region_ds.latitude.max().values)
    print("Region longitude range:", region_ds.longitude.min().values, "to", region_ds.longitude.max().values)