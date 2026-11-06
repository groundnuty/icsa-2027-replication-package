import xarray as xr

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Print basic information about the dataset
print("Dataset coordinates:")
print(ds.coords)
print("\nDataset variables:")
print(ds.data_vars)

# Check the dimensions
print(f"\nDimensions: {ds.dims}")
print(f"Time dimension: {ds.dims['time']}")
print(f"Latitude dimension: {ds.dims['lat']}")
print(f"Longitude dimension: {ds.dims['lon']}")

# Check some sample data
print(f"\nSample SST data shape: {ds.sst.shape}")
print(f"Sample SST data type: {ds.sst.dtype}")
print(f"Sample time values: {ds.time.values[:5]}")
print(f"Sample lat values: {ds.lat.values[:5]}")
print(f"Sample lon values: {ds.lon.values[:5]}")