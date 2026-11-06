
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Extract target data (2012-06-01 to 2012-08-31) for region
    target_sst = ds['analysed_sst'].isel(
        time=slice(11109, 11201),  # indices 11109 to 11200 inclusive
        latitude=slice(330, 390),  # indices 330 to 389 inclusive
        longitude=slice(551, 611)   # indices 551 to 610 inclusive
    )
    print("Target subset shape:", target_sst.shape)
    
    # Load the data
    target_data = target_sst.load()
    print("Loaded target data")
    
    # Check for NaN
    print("NaN fraction:", np.isnan(target_data.values).mean())
    print("Min:", np.nanmin(target_data.values), "Max:", np.nanmax(target_data.values))
