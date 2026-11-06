
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Extract baseline data (1991-12-27 to 2003-01-05) for region
    # First try loading the subset
    baseline_sst = ds['analysed_sst'].isel(
        time=slice(3647, 7675),  # indices 3647 to 7674 inclusive
        latitude=slice(330, 390),  # indices 330 to 389 inclusive
        longitude=slice(551, 611)   # indices 551 to 610 inclusive
    )
    print("Baseline subset shape:", baseline_sst.shape)
    
    # Load the data
    baseline_data = baseline_sst.load()
    print("Loaded baseline data")
    
    # Check for NaN
    print("NaN fraction:", np.isnan(baseline_data.values).mean())
    print("Min:", np.nanmin(baseline_data.values), "Max:", np.nanmax(baseline_data.values))
    print("Some values:", baseline_data.values[0, 0, :5])
