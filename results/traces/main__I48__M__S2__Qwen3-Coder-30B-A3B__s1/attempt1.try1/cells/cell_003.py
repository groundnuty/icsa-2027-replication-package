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
print(f"Time dimension size: {ds.sizes['time']}")
print(f"Latitude dimension size: {ds.sizes['latitude']}")
print(f"Longitude dimension size: {ds.sizes['longitude']}")

# Check some sample data
print(f"\nSample SST data shape: {ds.analysed_sst.shape}")
print(f"Sample SST data type: {ds.analysed_sst.dtype}")
print(f"Sample time values: {ds.time.values[:5]}")
print(f"Sample lat values: {ds.latitude.values[:5]}")
print(f"Sample lon values: {ds.longitude.values[:5]}")