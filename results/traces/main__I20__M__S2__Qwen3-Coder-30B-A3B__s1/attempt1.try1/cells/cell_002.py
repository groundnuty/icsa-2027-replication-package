import xarray as xr

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Print basic info about the dataset
print("Dataset dimensions:", ds.dims)
print("Dataset variables:", list(ds.data_vars.keys()))
print("Dataset coordinates:", list(ds.coords.keys()))

# Check the SST variable specifically
if 'sst' in ds.data_vars:
    print("\nSST variable shape:", ds.sst.shape)
    print("SST variable dimensions:", ds.sst.dims)
    print("SST variable coordinates:")
    print("  lat:", ds.sst.lat.min().values, "to", ds.sst.lat.max().values)
    print("  lon:", ds.sst.lon.min().values, "to", ds.sst.lon.max().values)
    print("  time:", ds.sst.time.min().values, "to", ds.sst.time.max().values)
    
    # Show first few time steps
    print("First few time steps:", ds.sst.time.isel(time=slice(0, 5)).values)

ds.close()