import xarray as xr

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Check the SST variable in detail
print("SST variable shape:", ds.analysed_sst.shape)
print("SST variable dimensions:", ds.analysed_sst.dims)
print("Latitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
print("Time range:", ds.time.min().values, "to", ds.time.max().values)

# Check if there are any missing values in the first few time steps
print("\nSample data from first time step:")
sample_data = ds.analysed_sst.isel(time=0)
print("Shape:", sample_data.shape)
print("Sample values (first 5x5):")
print(sample_data.isel(latitude=slice(0,5), longitude=slice(0,5)))

ds.close()