import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Define our region and period
region = {
    "lat_min": 56.63,
    "lat_max": 57.83,
    "lon_min": 20.23,
    "lon_max": 21.43
}

target_period = {
    "start": "2008-06-01",
    "end": "2008-08-31"
}

baseline_period = {
    "start": "1992-01-01",
    "end": "2002-12-31"
}

def date_to_doy(date_str):
    """Convert date string to day of year (1-366)"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60  # February 29th is day 60
    
    # Create a date for the same year but January 1st to compute DOY
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Adjust for leap years - if it's Feb 29 or later in a non-leap year, we need to adjust
    if not is_leap_year(date.year) and date.month > 2:
        if doy >= 60:  # If it's after Feb 29th in a non-leap year
            doy -= 1
    
    return doy

def is_leap_year(year):
    """Check if a year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def get_date_range(start_date, end_date):
    """Generate a list of dates between start and end (inclusive)"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def main():
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    # Let's examine the file listing more carefully
    dataset_dir = 'icsa2027_data_20261101T090944Z/s1z'
    files = fs.ls(dataset_dir)
    
    # Print first few files to understand the pattern
    print("First 10 files:")
    for i, f in enumerate(files[:10]):
        print(f"  {f}")
    
    # Look for a specific date range to make sure we understand the data
    print("\nLooking for 2008 files...")
    sst_files = [f for f in files if f.endswith('.nc') and 'sst_' in f]
    sst_files.sort()
    
    print(f"Total SST files: {len(sst_files)}")
    
    # Check what years we have
    years = set()
    for f in sst_files:
        filename = os.path.basename(f)
        if 'sst_' in filename:
            date_part = filename.split('_')[1].split('.')[0]  # Extract YYYYMMDD part
            year = int(date_part[:4])
            years.add(year)
    
    print(f"Years found: {sorted(years)}")
    
    # Filter for the required periods
    baseline_files = []
    target_files = []
    
    for f in sst_files:
        filename = os.path.basename(f)
        if 'sst_' in filename:
            date_part = filename.split('_')[1].split('.')[0]  # Extract YYYYMMDD part
            year = int(date_part[:4])
            
            if 1992 <= year <= 2002:
                baseline_files.append(f)
            elif year == 2008:
                target_files.append(f)
    
    print(f"Baseline files (1992-2002): {len(baseline_files)}")
    print(f"Target files (2008): {len(target_files)}")
    
    # Try to read a few files to understand the structure
    print("\nTrying to read sample data...")
    try:
        # Try to read one baseline file
        if baseline_files:
            sample_file = baseline_files[0]
            print(f"Reading sample baseline file: {sample_file}")
            with fs.open(sample_file, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                print("Dataset keys:", list(ds.keys()))
                print("Coordinates:", list(ds.coords))
                print("Shape:", ds['analysed_sst'].shape)
                print("Sample values (first 5x5):")
                print(ds['analysed_sst'].isel(time=0).values[:5, :5])
                print("Latitude range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
                print("Longitude range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)
        else:
            print("No baseline files found!")
            
    except Exception as e:
        print(f"Error reading sample data: {e}")
        
    # Create a simple report for now
    report = {
        "region": region,
        "baseline_analysed": baseline_period,
        "target_analysed": target_period,
        "events": [],
        "complete": False,
        "caveats": "Could not read data due to file access issues."
    }
    
    # Write report
    with open("output/report.json", "w") as f:
        import json
        json.dump(report, f, indent=2)
    
    print("Basic setup complete.")

if __name__ == "__main__":
    main()