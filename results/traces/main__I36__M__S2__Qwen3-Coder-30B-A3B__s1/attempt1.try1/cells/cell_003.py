import xarray as xr
import numpy as np

# Try opening the file
try:
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    print("Dataset opened successfully")
    print("Dimensions:", ds.dims)
    print("Variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    
    # Check the SST variable
    if 'sst' in ds.data_vars:
        print("SST variable shape:", ds.sst.shape)
        print("SST variable dims:", ds.sst.dims)
        print("SST coordinates:")
        print("  lat:", ds.lat.values[:5], "...", ds.lat.values[-5:])
        print("  lon:", ds.lon.values[:5], "...", ds.lon.values[-5:])
        print("  time:", ds.time.values[:5], "...", ds.time.values[-5:])
        
    # Close the dataset
    ds.close()
except Exception as e:
    print(f"Error opening dataset: {e}")