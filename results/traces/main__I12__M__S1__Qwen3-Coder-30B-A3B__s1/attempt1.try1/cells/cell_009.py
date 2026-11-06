import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Define our region of interest
LAT_MIN, LAT_MAX = 56.09, 57.29
LON_MIN, LON_MAX = 10.55, 11.75

# Define periods
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)
TARGET_START = datetime(2009, 6, 1)
TARGET_END = datetime(2009, 8, 31)

def date_to_doy(date):
    """Convert date to day of year (1-366) - treating all years as non-leap"""
    # For simplicity and consistency in calculations, treat all years as non-leap
    # This means Feb 29 doesn't exist in our DOY system
    jan1 = datetime(2001, 1, 1)  # Non-leap year
    doy = (date - jan1).days + 1
    return doy

def doy_to_date(doy):
    """Convert day of year to date (assuming non-leap year)"""
    jan1 = datetime(2001, 1, 1)
    date = jan1 + timedelta(days=doy-1)
    return date

# Function to load data for a specific date range and region
def load_region_data(start_date, end_date, region_lat_min, region_lat_max, region_lon_min, region_lon_max):
    """Load SST data for the specified region and date range"""
    # We'll need to collect data from individual files
    all_sst_data = []
    all_times = []
    
    current_date = start_date
    while current_date <= end_date:
        # Format filename based on date
        filename = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{current_date.strftime('%Y%m%d')}.nc"
        
        if os.path.exists(filename):
            try:
                ds = xr.open_dataset(filename, engine="h5netcdf")
                # Extract SST data
                sst = ds['analysed_sst'].squeeze()  # Remove time dimension
                
                # Get coordinates
                lats = ds['latitude'].values
                lons = ds['longitude'].values
                
                # Find indices for our region
                lat_indices = np.where((lats >= region_lat_min) & (lats <= region_lat_max))[0]
                lon_indices = np.where((lons >= region_lon_min) & (lons <= region_lon_max))[0]
                
                if len(lat_indices) > 0 and len(lon_indices) > 0:
                    # Extract subset for our region
                    sst_subset = sst[np.min(lat_indices):np.max(lat_indices)+1, 
                                    np.min(lon_indices):np.max(lon_indices)+1]
                    
                    all_sst_data.append(sst_subset.values)
                    all_times.append(current_date)
                else:
                    print(f"No data for region on {current_date}")
                
                ds.close()
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        else:
            print(f"File not found: {filename}")
            
        current_date += timedelta(days=1)
    
    if all_sst_data:
        # Stack all data along time dimension
        stacked_sst = np.stack(all_sst_data, axis=0)
        times = np.array(all_times)
        return stacked_sst, times
    else:
        return None, None

# Load baseline data to compute thresholds and climatology
print("Loading baseline data...")
baseline_sst, baseline_times = load_region_data(
    BASELINE_START, BASELINE_END, 
    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX
)

if baseline_sst is not None:
    print(f"Loaded baseline data: {baseline_sst.shape} for {len(baseline_times)} days")
else:
    print("Failed to load baseline data")

# Load target data for MHW detection
print("Loading target data...")
target_sst, target_times = load_region_data(
    TARGET_START, TARGET_END,
    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX
)

if target_sst is not None:
    print(f"Loaded target data: {target_sst.shape} for {len(target_times)} days")
else:
    print("Failed to load target data")