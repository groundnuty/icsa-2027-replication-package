import fsspec
import xarray as xr
import numpy as np

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Try to open the dataset
try:
    with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print("Dataset dimensions:", dict(ds.dims))
        print("Dataset variables:", list(ds.data_vars.keys()))
        print("Coordinates:")
        for coord in ds.coords:
            print(f"  {coord}: {ds[coord].shape}")
        
        # Check the actual coordinate values
        print("\nFirst few values of latitude:", ds['latitude'].values[:5])
        print("Last few values of latitude:", ds['latitude'].values[-5:])
        print("First few values of longitude:", ds['longitude'].values[:5])
        print("Last few values of longitude:", ds['longitude'].values[-5:])
        
        # Check time range
        print("\nTime range:")
        print("First few times:", ds['time'].values[:5])
        print("Last few times:", ds['time'].values[-5:])
        
        # Show the SST data shape
        print("\nSST data shape:", ds['analysed_sst'].shape)
        
except Exception as e:
    print(f"Error opening dataset: {e}")