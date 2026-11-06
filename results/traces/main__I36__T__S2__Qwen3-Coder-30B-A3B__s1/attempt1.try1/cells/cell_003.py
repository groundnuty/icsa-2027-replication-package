import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Define region and time period
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21
start_date = datetime(2003, 6, 1)
end_date = datetime(2003, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Open the dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Select the region
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Select the time period
    ds_period = ds_region.sel(time=slice(start_date, end_date))
    
    # Select baseline period for climatology calculation
    ds_baseline = ds_region.sel(time=slice(baseline_start, baseline_end))
    
    print(f"Region selection: lat {lat_min} to {lat_max}, lon {lon_min} to {lon_max}")
    print(f"Target period: {start_date.date()} to {end_date.date()}")
    print(f"Baseline period: {baseline_start.date()} to {baseline_end.date()}")
    print(f"Selected region shape: {ds_region['analysed_sst'].shape}")
    print(f"Target period shape: {ds_period['analysed_sst'].shape}")
    print(f"Baseline period shape: {ds_baseline['analysed_sst'].shape}")
    
    # Extract the data we need
    sst_data = ds_period['analysed_sst'].values
    baseline_data = ds_baseline['analysed_sst'].values
    times = ds_period['time'].values
    lats = ds_region['latitude'].values
    lons = ds_region['longitude'].values
    
    print(f"SST data shape: {sst_data.shape}")
    print(f"Times shape: {times.shape}")
    print(f"Latitudes shape: {lats.shape}")
    print(f"Longitudes shape: {lons.shape}")