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

def calculate_threshold_and_climatology(sst_data, baseline_start, baseline_end):
    """
    Calculate thresholds and climatology for each day of year using baseline period.
    Returns threshold and climatology arrays of length 366.
    """
    # Initialize arrays
    threshold = np.full(366, np.nan)
    climatology = np.full(366, np.nan)
    
    # Process each day of year
    for doy in range(1, 367):
        # Skip day 60 (Feb 29) as specified
        if doy == 60:
            continue
            
        # Get all baseline dates for this doy
        window_dates = get_baseline_window_dates(doy, baseline_start, baseline_end)
        
        # Collect all SST values from these dates
        sst_values = []
        
        # For each window date, collect SST data
        for win_date in window_dates:
            # Find matching data in our dataset
            # This will be done later when we load the actual data
            
            # For now, just collect the dates
            sst_values.extend(sst_data.get_sst_for_date(win_date))
            
        # Convert to numpy array and compute statistics
        sst_array = np.array(sst_values)
        sst_array = sst_array[np.isfinite(sst_array)]  # Remove NaN values
        
        if len(sst_array) > 0:
            # 90th percentile using method="hazen" (Hyndman-Fan type 5)
            threshold[doy-1] = np.quantile(sst_array, 0.9, method='hazen')
            climatology[doy-1] = np.mean(sst_array)
    
    # Handle day 60 (Feb 29) - set to mean of days 59 and 61
    if not np.isnan(climatology[58]) and not np.isnan(climatology[60]):
        climatology[59] = (climatology[58] + climatology[60]) / 2
    if not np.isnan(threshold[58]) and not np.isnan(threshold[60]):
        threshold[59] = (threshold[58] + threshold[60]) / 2
    
    return threshold, climatology

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

# Test the date conversion
test_dates = [
    datetime(2021, 1, 1),   # Should be day 1
    datetime(2021, 2, 28),  # Should be day 59  
    datetime(2021, 3, 1),   # Should be day 61
    datetime(2020, 2, 29),  # Leap year - should be day 60
]

for d in test_dates:
    print(f"{d.strftime('%Y-%m-%d')} -> DOY {date_to_doy(d)}")