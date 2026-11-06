import xarray as xr

# Load a sample file to understand the structure
sample_file = "/data/icsa2027_data_20231231.nc"
try:
    # Try different possible paths
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    
    # Check for sst variable
    if 'sst' in ds:
        print("\nSST variable found with shape:", ds['sst'].shape)
    elif 'analysed_sst' in ds:
        print("\nAnalysed_sst variable found with shape:", ds['analysed_sst'].shape)
    else:
        print("\nNo SST variable found!")
        
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")

# Try another approach with s1z path
try:
    sample_file_s1z = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
    ds = xr.open_dataset(sample_file_s1z, engine="h5netcdf")
    print("\n\nS1Z sample file:")
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    
    if 'sst' in ds:
        print("\nSST variable found with shape:", ds['sst'].shape)
    elif 'analysed_sst' in ds:
        print("\nAnalysed_sst variable found with shape:", ds['analysed_sst'].shape)
    else:
        print("\nNo SST variable found!")
        
    ds.close()
except Exception as e:
    print(f"Error opening s1z file: {e}")