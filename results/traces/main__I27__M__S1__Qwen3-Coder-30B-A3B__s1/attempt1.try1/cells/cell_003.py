import xarray as xr
import numpy as np

# Let's examine the actual SST variable in detail
sample_file = "/data/icsa2027_data_20230601.nc"
try:
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    
    # Look for SST-related variables
    print("All data variables:")
    for var in ds.data_vars:
        print(f"  {var}: {ds[var].dims}")
        
    # Check if there's a specific SST variable
    sst_var = None
    for var in ['sst', 'analysed_sst', 'temperature']:
        if var in ds.data_vars:
            sst_var = var
            break
    
    if sst_var:
        print(f"\nUsing SST variable: {sst_var}")
        sst_data = ds[sst_var]
        print(f"SST data shape: {sst_data.shape}")
        print(f"SST data dtype: {sst_data.dtype}")
        print(f"SST dimensions: {sst_data.dims}")
        
        # Check some sample data
        print(f"Sample values (first 5): {sst_data.isel(time=0, lat=0, lon=0).values}")
        print(f"Sample values (first 5): {sst_data.isel(time=0, lat=10, lon=10).values}")
        
        # Check coordinates
        print(f"\nLatitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
        print(f"Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")
    else:
        print("No SST variable found!")
        
    ds.close()
except Exception as e:
    print(f"Error: {e}")