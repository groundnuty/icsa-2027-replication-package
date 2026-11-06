import numpy as np
from scipy import stats

def date_to_doy(date):
    """Convert a date (datetime64) to day of year (1-366)"""
    # Convert to datetime object for easier manipulation
    dt = date.astype(datetime)
    # Get day of year (1-366)
    doy = dt.timetuple().tm_yday
    # Handle leap year special case for Feb 29
    if is_leap_year(dt.year) and doy > 60:
        doy -= 1
    return doy

def is_leap_year(year):
    """Check if a year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def calculate_doy_array():
    """Create a mapping from date to day of year"""
    doy_array = np.zeros(366, dtype=int)
    # Create a reference date for year 2000 (a leap year)
    ref_year = 2000
    
    for i in range(366):
        # Create a date for day i of the year (1-indexed)
        if i < 31:  # January
            month, day = 1, i + 1
        elif i < 59:  # February (non-leap year)
            month, day = 2, i - 30
        elif i < 90:  # March
            month, day = 3, i - 58
        elif i < 120:  # April
            month, day = 4, i - 89
        elif i < 151:  # May
            month, day = 5, i - 119
        elif i < 181:  # June
            month, day = 6, i - 150
        elif i < 212:  # July
            month, day = 7, i - 180
        elif i < 243:  # August
            month, day = 8, i - 211
        elif i < 273:  # September
            month, day = 9, i - 242
        elif i < 304:  # October
            month, day = 10, i - 272
        elif i < 334:  # November
            month, day = 11, i - 303
        else:  # December
            month, day = 12, i - 333
            
        # Create date and get day of year
        try:
            dt = datetime(ref_year, month, day)
            doy = dt.timetuple().tm_yday
            # Adjust for leap year if needed
            if is_leap_year(ref_year) and doy > 60:
                doy -= 1
            doy_array[i] = doy
        except:
            doy_array[i] = 0
    return doy_array

def get_baseline_dates(start_year, end_year):
    """Get all dates in the baseline period"""
    dates = []
    for year in range(start_year, end_year + 1):
        # Create all dates for this year
        for day in range(1, 367):  # 1-366
            try:
                if day == 60:  # Special handling for Feb 29
                    continue
                # Create date for day of year
                if day <= 31:
                    month, day_of_month = 1, day
                elif day <= 59:
                    month, day_of_month = 2, day - 31
                elif day <= 90:
                    month, day_of_month = 3, day - 59
                elif day <= 120:
                    month, day_of_month = 4, day - 90
                elif day <= 151:
                    month, day_of_month = 5, day - 120
                elif day <= 181:
                    month, day_of_month = 6, day - 151
                elif day <= 212:
                    month, day_of_month = 7, day - 181
                elif day <= 243:
                    month, day_of_month = 8, day - 212
                elif day <= 273:
                    month, day_of_month = 9, day - 243
                elif day <= 304:
                    month, day_of_month = 10, day - 273
                elif day <= 334:
                    month, day_of_month = 11, day - 304
                else:
                    month, day_of_month = 12, day - 334
                    
                # Check if this is valid
                if month <= 12 and day_of_month <= 31:
                    date = datetime(year, month, day_of_month)
                    dates.append(np.datetime64(date))
            except:
                pass
    return dates

# Actually, let's make a simpler approach
def get_day_of_year_mapping():
    """Create a mapping from date to day of year for all dates in 1992-2002"""
    doy_map = {}
    # We'll process each day manually for simplicity
    base_years = list(range(1992, 2003))  # 1992 to 2002 inclusive
    
    for year in base_years:
        is_leap = is_leap_year(year)
        # Create all dates for this year
        for month in range(1, 13):
            if month in [1, 3, 5, 7, 8, 10, 12]:
                days_in_month = 31
            elif month in [4, 6, 9, 11]:
                days_in_month = 30
            else:  # February
                days_in_month = 29 if is_leap else 28
                
            for day in range(1, days_in_month + 1):
                date = datetime(year, month, day)
                doy = date.timetuple().tm_yday
                # Adjust for leap year
                if is_leap and doy > 60:
                    doy -= 1
                doy_map[np.datetime64(date)] = doy
                
    return doy_map

# Let's simplify this approach
def compute_threshold_and_climatology(sst_data, baseline_start, baseline_end):
    """
    Compute thresholds and climatologies for each day of year.
    
    Parameters:
    sst_data: 3D array (time, lat, lon) containing SST data
    baseline_start: start date for baseline period
    baseline_end: end date for baseline period
    
    Returns:
    threshold: 366-element array of thresholds
    climatology: 366-element array of climatologies
    """
    
    # Create day-of-year mapping for baseline period
    baseline_dates = []
    baseline_doy = []
    
    # Generate all dates from baseline_start to baseline_end
    start_dt = baseline_start.astype(datetime)
    end_dt = baseline_end.astype(datetime)
    
    current_date = start_dt
    while current_date <= end_dt:
        baseline_dates.append(np.datetime64(current_date))
        # Calculate day of year
        doy = current_date.timetuple().tm_yday
        # Adjust for leap year
        if is_leap_year(current_date.year) and doy > 60:
            doy -= 1
        baseline_doy.append(doy)
        current_date += timedelta(days=1)
        
    # Create mapping from date to day of year
    date_to_doy = dict(zip(baseline_dates, baseline_doy))
    
    # Initialize arrays for storing pools for each day of year
    # We'll store all SST values for each day of year (excluding day 60)
    pools = [[] for _ in range(367)]  # Index 0 unused, days 1-366
    
    # Go through all time points in the data and add to appropriate pools
    for t in range(len(sst_data.time)):
        date = sst_data.time[t].values
        doy = date_to_doy[date]
        
        # Skip day 60 (Feb 29) as specified
        if doy == 60:
            continue
            
        # Add all SST values for this day to the pool
        sst_slice = sst_data.analysed_sst[t, :, :]
        # Flatten and filter out NaN values
        sst_values = sst_slice.values.flatten()
        valid_values = sst_values[~np.isnan(sst_values)]
        
        pools[doy].extend(valid_values)
        
    # Now handle day 60 specially (it gets values from neighbors)
    # For day 60, we'll combine values from days 59 and 61
    # But we also need to handle the special case where we might not have enough data
    if len(pools[59]) > 0 and len(pools[61]) > 0:
        # Combine pools for day 60 (average of 59 and 61)
        combined_pool = pools[59] + pools[61]
        pools[60] = combined_pool
    elif len(pools[59]) > 0:
        pools[60] = pools[59]
    elif len(pools[61]) > 0:
        pools[60] = pools[61]
    
    # Compute thresholds and climatologies for each day of year
    threshold = np.full(367, np.nan)  # Index 0 unused, days 1-366
    climatology = np.full(367, np.nan)
    
    for doy in range(1, 367):
        if len(pools[doy]) > 0:
            # Use numpy's method="hazen" equivalent (which is same as quantile with method='linear')
            threshold[doy] = np.quantile(pools[doy], 0.9, method='linear')
            climatology[doy] = np.mean(pools[doy])
            
    # Apply smoothing (31-day centered moving average that wraps around)
    threshold_smoothed = smooth_366_array(threshold)
    climatology_smoothed = smooth_366_array(climatology)
    
    return threshold_smoothed, climatology_smoothed

def smooth_366_array(arr):
    """Apply 31-day centered moving average that wraps around"""
    smoothed = np.zeros_like(arr)
    window_size = 31
    half_window = window_size // 2
    
    for i in range(1, 367):  # Days 1-366
        # Sum values in the window
        window_sum = 0
        count = 0
        
        for j in range(-half_window, half_window + 1):
            # Wrap around the year
            wrapped_idx = ((i + j - 1) % 366) + 1  # Convert to 1-based indexing
            if not np.isnan(arr[wrapped_idx]):
                window_sum += arr[wrapped_idx]
                count += 1
                
        if count > 0:
            smoothed[i] = window_sum / count
        else:
            smoothed[i] = np.nan
            
    return smoothed

# Test the functions
print("Testing helper functions...")