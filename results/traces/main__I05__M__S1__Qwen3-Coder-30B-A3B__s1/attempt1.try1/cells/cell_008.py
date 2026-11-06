import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Define region and period
LAT_MIN, LAT_MAX = 54.39, 55.59
LON_MIN, LON_MAX = 18.25, 19.45
START_DATE = datetime(2021, 6, 1)
END_DATE = datetime(2021, 8, 31)
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)

# Create output directory
os.makedirs('output', exist_ok=True)

def date_to_doy(date):
    """Convert a date to day-of-year (1-366)"""
    # Handle leap year cases properly
    if date.month == 2 and date.day == 29:
        return 60
    
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Adjust for leap year if needed
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        if doy >= 60:  # After Feb 29
            doy += 1
            
    return doy

def get_baseline_window_dates(doy, baseline_start, baseline_end):
    """Get all dates in baseline period that fall within ±5 days of a date with the given doy"""
    window_dates = []
    
    # Get the range of dates to check
    for year in range(baseline_start.year, baseline_end.year + 1):
        # Find the date that corresponds to this doy in this year
        try:
            # Create a date for Jan 1 of this year
            jan1 = datetime(year, 1, 1)
            
            # Calculate the target date
            target_date = jan1 + timedelta(days=doy - 1)
            
            # Add dates within ±5 days
            for i in range(-5, 6):
                candidate_date = target_date + timedelta(days=i)
                
                # Make sure it's within baseline period
                if baseline_start <= candidate_date <= baseline_end:
                    window_dates.append(candidate_date)
                    
        except ValueError:
            # Skip invalid dates (like Feb 29 in non-leap years)
            continue
    
    return window_dates

def smooth_with_wrapping(arr, window_size=31):
    """
    Apply a centered moving average with wrapping around the year.
    """
    # Ensure array is 366 elements
    if len(arr) != 366:
        raise ValueError("Array must be of length 366")
    
    smoothed = np.zeros_like(arr)
    half_window = window_size // 2
    
    for i in range(366):
        # Calculate the indices with wrapping
        indices = [(i + j - half_window) % 366 for j in range(window_size)]
        # Take the valid values (excluding NaN)
        values = arr[indices]
        valid_values = values[np.isfinite(values)]
        
        if len(valid_values) > 0:
            smoothed[i] = np.mean(valid_values)
        else:
            smoothed[i] = np.nan
    
    return smoothed

def find_sea_cells(sst_data, lat_min, lat_max, lon_min, lon_max):
    """
    Find sea cells (grid cells with finite SST on every day of target period)
    """
    # Extract the region
    region_data = sst_data.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Get all time steps in target period
    target_times = [t for t in region_data.time.values 
                   if START_DATE <= datetime.strptime(str(t)[:10], '%Y-%m-%d') <= END_DATE]
    
    # For each grid cell, check if it has finite values for all target days
    sea_cells = []
    latitudes = region_data.latitude.values
    longitudes = region_data.longitude.values
    
    # Check each cell
    for i, lat in enumerate(latitudes):
        for j, lon in enumerate(longitudes):
            # Extract time series for this cell
            cell_sst = region_data.analysed_sst.isel(latitude=i, longitude=j)
            # Check if all target days have finite values
            valid_count = np.sum(np.isfinite(cell_sst.values))
            if valid_count == len(target_times):
                sea_cells.append((lat, lon))
    
    return sea_cells

# Let's test loading some data to understand the file structure better
def load_sample_data():
    """Load sample data to understand the structure"""
    # Load a few sample files to understand the data structure
    base_path = "/data/icsa2027_data_20261101T090944Z/s1z"
    
    # Look for a few files in the target period
    sample_files = []
    for filename in sorted(os.listdir(base_path))[:5]:  # Just take first 5
        if filename.startswith('sst_') and filename.endswith('.nc'):
            sample_files.append(filename)
    
    print("Sample files:", sample_files)
    
    # Try to load one file to understand structure
    if sample_files:
        file_path = os.path.join(base_path, sample_files[0])
        try:
            ds = xr.open_dataset(file_path, engine="h5netcdf")
            print("\nSample dataset structure:")
            print("Variables:", list(ds.data_vars.keys()))
            print("Coordinates:", list(ds.coords.keys()))
            if 'analysed_sst' in ds.data_vars:
                print("analysed_sst shape:", ds.analysed_sst.shape)
                print("latitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
                print("longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
            ds.close()
        except Exception as e:
            print(f"Error loading sample file: {e}")

load_sample_data()