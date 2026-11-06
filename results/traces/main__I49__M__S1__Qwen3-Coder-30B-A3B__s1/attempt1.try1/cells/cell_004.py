import xarray as xr
import numpy as np

# Load a sample file to understand the structure properly
sample_file = "/data/icsa2027_data_20231231.nc"
try:
    # Try to load from the s1z directory directly
    sample_file = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Dataset coordinates and variables:")
    print(ds.coords)
    print("\nVariables:")
    print(ds.data_vars)
    
    # Check the actual coordinate names
    print("\nCoordinate names:")
    for coord in ds.coords:
        print(f"  {coord}: {ds.coords[coord].shape}")
        
    print("\nLatitude range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
    print("Longitude range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)
    
    # Check some SST data
    print("\nSample SST data shape:", ds['analysed_sst'].shape)
    print("Sample SST data (first few values):", ds['analysed_sst'][0, 0, :5].values)
    
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")