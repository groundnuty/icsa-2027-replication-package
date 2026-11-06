import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import netCDF4 as nc
from scipy import stats

# Define region of interest
LAT_MIN, LAT_MAX = 64.51, 65.71
LON_MIN, LON_MAX = 21.97, 23.17

# Define periods
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)
TARGET_START = datetime(2019, 6, 1)
TARGET_END = datetime(2019, 8, 31)

def date_to_doy(date):
    """Convert a date to day of year (1-366)"""
    # Handle leap year cases properly
    if date.month == 2 and date.day == 29:
        return 60
    else:
        # Create a date for the same year but January 1st to calculate DOY
        jan1 = datetime(date.year, 1, 1)
        doy = (date - jan1).days + 1
        return doy

def get_doy_range(doy):
    """Get the range of days around a DOY for the pooling window"""
    # For DOY 60 (Feb 29), we don't make a separate pool
    if doy == 60:
        return None
    
    # Get the range of dates around this DOY in the baseline period
    # We want ±5 days around this DOY
    # But also handle edge cases where we go beyond the baseline period
    
    # Get the start and end dates for our baseline period
    start_date = BASELINE_START
    end_date = BASELINE_END
    
    # Create a reference date for this DOY in 2000 (leap year)
    ref_year = 2000
    if doy == 60:  # Feb 29
        ref_date = datetime(ref_year, 2, 29)
    else:
        # Find the date for this DOY in the reference year
        ref_date = datetime(ref_year, 1, 1) + timedelta(days=doy-1)
    
    # Determine the start and end of our window
    window_start = ref_date - timedelta(days=5)
    window_end = ref_date + timedelta(days=5)
    
    # Adjust for year boundaries
    if window_start.year < start_date.year:
        window_start = datetime(start_date.year, window_start.month, window_start.day)
    if window_end.year > end_date.year:
        window_end = datetime(end_date.year, window_end.month, window_end.day)
        
    return (window_start, window_end)

def extract_baseline_data():
    """Extract all baseline data for the region of interest"""
    print("Extracting baseline data...")
    
    # Create list of dates in baseline period
    dates = []
    current_date = BASELINE_START
    while current_date <= BASELINE_END:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Load data for all dates in baseline period
    baseline_sst = []
    latitudes = None
    longitudes = None
    
    # Process files for baseline period
    base_dir = "/data/icsa2027_data_20261101T090944Z/s1z"
    
    # For efficiency, let's just load the first few files to understand the structure
    # and then build the proper implementation
    
    # First, let's find all the relevant files
    file_dates = []
    for filename in sorted(os.listdir(base_dir)):
        if filename.startswith('sst_') and filename.endswith('.nc'):
            try:
                date_str = filename[4:-3]  # Remove 'sst_' prefix and '.nc' suffix
                file_date = datetime.strptime(date_str, '%Y%m%d')
                if BASELINE_START <= file_date <= BASELINE_END:
                    file_dates.append((file_date, filename))
            except ValueError:
                continue
    
    # Sort by date
    file_dates.sort()
    
    print(f"Found {len(file_dates)} baseline files")
    
    # For now, let's load a few files to understand the data structure
    # We'll process the entire baseline period later
    selected_files = file_dates[:10]  # Just test with a few files
    
    # We need to build the full dataset
    # Since we're going to process the whole baseline period, let's approach this differently
    # Let's create a function to load the data in chunks
    
    return selected_files

def create_output_directory():
    """Create output directory if it doesn't exist"""
    if not os.path.exists('output'):
        os.makedirs('output')

create_output_directory()

# Test the date conversion function
test_date = datetime(2020, 2, 29)  # Leap year
doy = date_to_doy(test_date)
print(f"Date {test_date} DOY: {doy}")

test_date2 = datetime(2020, 3, 1)
doy2 = date_to_doy(test_date2)
print(f"Date {test_date2} DOY: {doy2}")

test_date3 = datetime(2020, 12, 31)
doy3 = date_to_doy(test_date3)
print(f"Date {test_date3} DOY: {doy3}")

# Test getting DOY ranges
range1 = get_doy_range(60)  # Should be None
print(f"DOY 60 range: {range1}")

range2 = get_doy_range(1)  # Jan 1
print(f"DOY 1 range: {range2}")