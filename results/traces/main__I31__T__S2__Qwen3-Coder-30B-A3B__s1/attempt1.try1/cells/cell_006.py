import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset and keep it open
f = fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Define our region boundaries
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

# Filter to our region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define our target period
start_date = datetime(2017, 6, 1)
end_date = datetime(2017, 8, 31)

# Filter to our time period
ds_period = ds_region.sel(time=slice(start_date, end_date))

# Get the actual SST data
sst_data = ds_period.analysed_sst.values  # Shape: (92, 60, 60)
print(f"SST data shape: {sst_data.shape}")

# Close the file since we've extracted what we needed
f.close()

# Now let's create a function to compute day-of-year for a datetime object
def date_to_doy(date):
    """Convert a date to day of year (1-366)"""
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")
    return date.timetuple().tm_yday

# Create the baseline period (1992-01-01 to 2002-12-31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Generate all baseline dates
baseline_dates = []
current = baseline_start
while current <= baseline_end:
    baseline_dates.append(current)
    current += timedelta(days=1)

print(f"Baseline period: {baseline_dates[0]} to {baseline_dates[-1]}")
print(f"Number of baseline days: {len(baseline_dates)}")

# Create a mapping from date to day-of-year for all baseline dates
date_to_doy_map = {date: date_to_doy(date) for date in baseline_dates}

# Create a reverse mapping: from DOY to all dates with that DOY
doy_to_dates = {}
for date in baseline_dates:
    doy = date_to_doy_map[date]
    if doy not in doy_to_dates:
        doy_to_dates[doy] = []
    doy_to_dates[doy].append(date)

print(f"DOY 1 has {len(doy_to_dates[1])} dates")
print(f"DOY 60 has {len(doy_to_dates[60])} dates (Feb 29)")
print(f"DOY 61 has {len(doy_to_dates[61])} dates")

# Now let's implement the core MHW detection algorithm
def compute_threshold_and_climatology(sst_data, time_coords, baseline_dates, date_to_doy_map):
    """
    Compute thresholds and climatology for each grid cell and day of year.
    """
    n_time, n_lat, n_lon = sst_data.shape
    
    # Initialize arrays for thresholds and climatology (366 days)
    thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
    
    # For each day of year (1-366)
    for doy in range(1, 367):
        print(f"Processing DOY {doy}...")
        
        # Special handling for day 60 (February 29)
        if doy == 60:
            # Pool for day 60 is all Feb 29 dates and their windows
            pool_values = []
            
            # Collect all Feb 29 dates and their windows
            for date in baseline_dates:
                if date_to_doy_map[date] == 60:
                    # Include dates within ±5 days of this date
                    for i in range(-5, 6):
                        candidate_date = date + timedelta(days=i)
                        # Ensure it's within valid range (1991-12-27 to 2003-01-05)
                        if datetime(1991, 12, 27) <= candidate_date <= datetime(2003, 1, 5):
                            # Find the corresponding index in baseline_dates
                            try:
                                idx = baseline_dates.index(candidate_date)
                                # Collect all valid SST values for this date across all cells
                                for lat_idx in range(n_lat):
                                    for lon_idx in range(n_lon):
                                        val = sst_data[idx, lat_idx, lon_idx]
                                        if np.isfinite(val):
                                            pool_values.append(val)
                            except ValueError:
                                continue  # Date not found in baseline dates
                            
            # Calculate threshold and climatology for day 60
            if pool_values:
                pool_array = np.array(pool_values)
                thresholds[doy-1] = np.nanpercentile(pool_array, 90, method='linear')
                climatology[doy-1] = np.nanmean(pool_array)
        else:
            # Pool for other days
            pool_values = []
            
            # Collect all dates with this DOY and their windows
            for date in baseline_dates:
                if date_to_doy_map[date] == doy:
                    # Include dates within ±5 days of this date
                    for i in range(-5, 6):
                        candidate_date = date + timedelta(days=i)
                        # Ensure it's within valid range (1991-12-27 to 2003-01-05)
                        if datetime(1991, 12, 27) <= candidate_date <= datetime(2003, 1, 5):
                            # Find the corresponding index in baseline_dates
                            try:
                                idx = baseline_dates.index(candidate_date)
                                # Collect all valid SST values for this date across all cells
                                for lat_idx in range(n_lat):
                                    for lon_idx in range(n_lon):
                                        val = sst_data[idx, lat_idx, lon_idx]
                                        if np.isfinite(val):
                                            pool_values.append(val)
                            except ValueError:
                                continue  # Date not found in baseline dates
            
            # Calculate threshold and climatology for this DOY
            if pool_values:
                pool_array = np.array(pool_values)
                thresholds[doy-1] = np.nanpercentile(pool_array, 90, method='linear')
                climatology[doy-1] = np.nanmean(pool_array)
    
    # Handle special case for day 60 (set to mean of days 59 and 61)
    if not np.isnan(thresholds[59]) and not np.isnan(thresholds[61]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    if not np.isnan(climatology[59]) and not np.isnan(climatology[61]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
    
    return thresholds, climatology

# Let's try a simpler approach - just get the time coordinates from the dataset
time_coords = ds_period.time.values
print(f"Time coordinates shape: {time_coords.shape}")

# Try to compute thresholds and climatology for just a small subset to test
# Let's first identify which cells have valid data for all days
print("Computing which cells have valid data for all days...")

# Get a smaller subset for testing
subset_sst = sst_data[:, :5, :5]  # First 5x5 grid points
print(f"Subset shape: {subset_sst.shape}")

# For demonstration, let's compute just for one cell to test
single_cell_sst = subset_sst[:, 0, 0]
print(f"Single cell SST shape: {single_cell_sst.shape}")

# Let's manually create a small test case to verify our approach works
print("Testing approach with simple synthetic data...")
test_sst = np.random.rand(10, 5, 5) * 30 + 270  # Random SST data in Kelvin
test_time = [datetime(2017, 6, 1 + i) for i in range(10)]
print(f"Test SST shape: {test_sst.shape}")
print(f"Test time: {test_time}")