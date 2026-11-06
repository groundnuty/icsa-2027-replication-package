import xarray as xr
import numpy as np

# Open the file again
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Look at the SST variable details
print("SST variable details:")
print("Shape:", ds.analysed_sst.shape)
print("Dimensions:", ds.analysed_sst.dims)
print("Coordinate ranges:")
print("  latitude:", ds.latitude.min().values, "to", ds.latitude.max().values)
print("  longitude:", ds.longitude.min().values, "to", ds.longitude.max().values)
print("  time:", ds.time.min().values, "to", ds.time.max().values)

# Check the actual variable name
print("\nVariable name:", list(ds.data_vars.keys()))

# Check some sample data
print("\nSample SST data (first few values):")
sample_sst = ds.analysed_sst.isel(time=0, latitude=0, longitude=0)
print(sample_sst.values)

# Close the dataset
ds.close()