import xarray as xr
import fsspec
import numpy as np
import datetime
import re

fs = fsspec.filesystem('onedata')

def date_to_doy(year, month, day):
    """Convert date to day of year (1-366)"""
    date_obj = datetime.date(year, month, day)
    doy = date_obj.timetuple().tm_yday
    
    # Special handling for Feb 29
    if month == 2 and day == 29:
        # In non-leap years, Feb 29 doesn't exist
        return 59  # Treat as Feb 28
    return doy

def get_all_sst_data():
    """Load all available SST data for analysis"""
    # Get all sst files
    files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
    sst_files = [f for f in files if 'sst_' in f and '.nc' in f]
    
    # Sort by date
    sst_files.sort()
    
    print(f"Found {len(sst_files)} SST files")
    
    # Load a sample to understand the data structure better
    with fs.open(sst_files[0], 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        lat_vals = ds.latitude.values
        lon_vals = ds.longitude.values
        ds.close()
        
    print(f"Latitude range: {lat_vals.min()} to {lat_vals.max()}")
    print(f"Longitude range: {lon_vals.min()} to {lon_vals.max()}")
    
    # Define our region of interest
    lat_min, lat_max = 57.33, 58.53
    lon_min, lon_max = 9.03, 10.23
    
    # Find indices for our region
    lat_indices = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
    lon_indices = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]
    
    print(f"Region indices: lat {len(lat_indices)}, lon {len(lon_indices)}")
    
    # Extract years from filenames
    years_available = set()
    for f in sst_files:
        match = re.search(r'sst_(\d{8})\.nc', f)
        if match:
            date_str = match.group(1)
            year = int(date_str[:4])
            years_available.add(year)
            
    print(f"Available years: {sorted(years_available)}")
    
    return {
        'lat_vals': lat_vals,
        'lon_vals': lon_vals,
        'lat_indices': lat_indices,
        'lon_indices': lon_indices,
        'available_years': sorted(years_available),
        'sst_files': sst_files
    }

# Get data info
try:
    data_info = get_all_sst_data()
except Exception as e:
    print(f"Error getting data info: {e}")
    # Try a simpler approach
    files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
    sst_files = [f for f in files if 'sst_' in f and '.nc' in f]
    print(f"First few files: {sst_files[:5]}")