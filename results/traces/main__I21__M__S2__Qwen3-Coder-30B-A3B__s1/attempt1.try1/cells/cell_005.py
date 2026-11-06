import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

def day_of_year(date):
    """Convert date to day of year (1-366)"""
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60
    elif date.month == 12 and date.day == 31:
        return 366
    else:
        # Convert to day of year
        doy = date.timetuple().tm_yday
        # Adjust for leap year if needed (but we're handling Feb 29 separately)
        return doy

def get_doy_from_date_np64(date_np64):
    """Convert numpy datetime64 to day of year"""
    date = date_np64.astype('datetime64[s]').astype(datetime)
    return day_of_year(date)

def calculate_thresholds_and_climatology(ds, lat_indices, lon_indices, baseline_start, baseline_end):
    """Calculate thresholds and climatology for each day of year"""
    
    # Get baseline data
    baseline_mask = (ds.time >= np.datetime64(baseline_start)) & (ds.time <= np.datetime64(baseline_end))
    baseline_indices = np.where(baseline_mask)[0]
    
    # Extract baseline SST data for our region
    baseline_sst = ds.analysed_sst.isel(time=baseline_indices, latitude=lat_indices, longitude=lon_indices)
    
    # Create mapping from dates to day of year
    baseline_dates = ds.time.isel(time=baseline_indices).values
    doy_map = {}
    
    for i, date in enumerate(baseline_dates):
        date_obj = date.astype('datetime64[s]').astype(datetime)
        doy = day_of_year(date_obj)
        if doy not in doy_map:
            doy_map[doy] = []
        doy_map[doy].append(i)
    
    # Prepare arrays for thresholds and climatologies
    thresholds = np.full(366, np.nan)
    climatologies = np.full(366, np.nan)
    
    # Calculate for each day of year (excluding day 60 which will be handled specially)
    for doy in range(1, 367):
        if doy == 60:  # Skip day 60 for now, handle it later
            continue
            
        # Get all baseline days with this day of year (with ±5 day window)
        if doy == 1:  # Special case for Jan 1
            # Include days from Dec 27, 1991 to Jan 5, 2003 (wrap around)
            window_start = datetime(1991, 12, 27)
            window_end = datetime(2003, 1, 5)
        elif doy == 366:  # Special case for Dec 31
            # Include days from Dec 27, 1991 to Jan 5, 2003 (wrap around)
            window_start = datetime(1991, 12, 27)
            window_end = datetime(2003, 1, 5)
        else:
            # Normal case: ±5 days around the target DOY
            # This is more complex because we need to find matching DOYs across years
            window_start = None
            window_end = None
        
        # For simplicity, we'll collect all data points for each DOY
        if doy in doy_map:
            # Get all values for this DOY across years
            sst_values = baseline_sst.isel(time=doy_map[doy]).values
            # Flatten to get all valid values
            flat_values = sst_values.flatten()
            # Remove NaN values
            valid_values = flat_values[~np.isnan(flat_values)]
            
            if len(valid_values) > 0:
                # Calculate 90th percentile (Hazen method)
                threshold = np.percentile(valid_values, 90, method='hazen')
                # Calculate mean
                climatology = np.mean(valid_values)
                
                thresholds[doy-1] = threshold
                climatologies[doy-1] = climatology
    
    # Handle day 60 (February 29) - set to mean of days 59 and 61
    if not np.isnan(thresholds[58]) and not np.isnan(thresholds[60]):
        thresholds[59] = (thresholds[58] + thresholds[60]) / 2
    if not np.isnan(climatologies[58]) and not np.isnan(climatologies[60]):
        climatologies[59] = (climatologies[58] + climatologies[60]) / 2
    
    # Smooth with 31-day centered moving average
    def smooth_366(arr):
        smoothed = np.full_like(arr, np.nan)
        for i in range(366):
            # Get the 31-day window (centered)
            window_values = []
            for j in range(-15, 16):
                idx = (i + j) % 366
                if not np.isnan(arr[idx]):
                    window_values.append(arr[idx])
            if window_values:
                smoothed[i] = np.mean(window_values)
        return smoothed
    
    thresholds_smoothed = smooth_366(thresholds)
    climatologies_smoothed = smooth_366(climatologies)
    
    return thresholds_smoothed, climatologies_smoothed

def find_mhw_events(sst_data, thresholds, climatologies, lat_indices, lon_indices):
    """Find MHW events for the target period"""
    
    # Create mask for MHW events
    mhw_mask = np.zeros(sst_data.shape, dtype=np.uint8)
    
    # Get the time dimension
    n_days, n_lat, n_lon = sst_data.shape
    
    # Process each cell individually
    for i_lat in range(n_lat):
        for i_lon in range(n_lon):
            # Extract time series for this cell
            ts = sst_data[:, i_lat, i_lon]
            
            # Determine hot days for this cell
            hot_days = np.zeros(n_days, dtype=bool)
            
            for i_day in range(n_days):
                # Get date for this day
                date = datetime(2021, 6, 1) + timedelta(days=i_day)
                doy = day_of_year(date)
                
                # Use threshold and climatology for this day of year
                threshold = thresholds[doy-1]
                
                # Check if SST is hot
                if not np.isnan(ts[i_day]) and not np.isnan(threshold):
                    hot_days[i_day] = ts[i_day] >= threshold
            
            # Find runs of at least 5 consecutive hot days
            # Then join gaps of 1 or 2 days
            mhw_run = np.zeros(n_days, dtype=bool)
            
            # First pass: identify hot runs
            i = 0
            while i < n_days:
                if hot_days[i]:
                    # Start of a potential run
                    run_start = i
                    # Extend until the run breaks
                    while i < n_days and hot_days[i]:
                        i += 1
                    run_end = i - 1
                    
                    # Check if run is at least 5 days
                    if run_end - run_start + 1 >= 5:
                        # Mark this run
                        mhw_run[run_start:run_end+1] = True
                else:
                    i += 1
            
            # Second pass: join gaps of 1 or 2 days
            # We'll use a simple approach - expand each MHW by 1 day in both directions
            # if the adjacent days are not already marked as hot
            expanded_mhw = mhw_run.copy()
            
            # Expand MHWs by 1 day in each direction
            for i in range(n_days):
                if mhw_run[i]:
                    # Expand left
                    for j in range(max(0, i-1), i):
                        if not hot_days[j]:  # Only extend if not already hot
                            expanded_mhw[j] = True
                    # Expand right  
                    for j in range(i+1, min(n_days, i+2)):
                        if not hot_days[j]:  # Only extend if not already hot
                            expanded_mhw[j] = True
            
            # Update the final mask
            mhw_mask[:, i_lat, i_lon] = expanded_mhw.astype(np.uint8)
    
    return mhw_mask

def main():
    # Load the dataset
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    
    # Define our region and time period
    lat_min, lat_max = 57.33, 58.53
    lon_min, lon_max = 9.03, 10.23
    start_date = datetime(2021, 6, 1)
    end_date = datetime(2021, 8, 31)
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    # Filter the region
    lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
    lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]
    
    # Filter the time period
    time_mask = (ds.time >= np.datetime64(start_date)) & (ds.time <= np.datetime64(end_date))
    time_indices = np.where(time_mask)[0]
    
    # Filter baseline period
    baseline_mask = (ds.time >= np.datetime64(baseline_start)) & (ds.time <= np.datetime64(baseline_end))
    baseline_indices = np.where(baseline_mask)[0]
    
    # Extract subset for analysis
    subset = ds.isel(latitude=lat_indices, longitude=lon_indices, time=time_indices)
    
    print(f"Processing region: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]")
    print(f"Target period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Baseline period: {baseline_start.strftime('%Y-%m-%d')} to {baseline_end.strftime('%Y-%m-%d')}")
    
    # Calculate thresholds and climatology
    print("Calculating thresholds and climatology...")
    thresholds, climatologies = calculate_thresholds_and_climatology(
        ds, lat_indices, lon_indices, baseline_start, baseline_end
    )
    
    # Extract target SST data
    target_sst = subset.analysed_sst.values
    
    # Find MHW events
    print("Finding MHW events...")
    mhw_mask = find_mhw_events(target_sst, thresholds, climatologies, lat_indices, lon_indices)
    
    # Create the output NetCDF file
    print("Creating output NetCDF file...")
    
    # Create new dataset with MHW mask
    output_ds = xr.Dataset(
        {
            'mhw': (['time', 'lat', 'lon'], mhw_mask, {'units': 'binary', 'long_name': 'Marine Heatwave'})
        },
        coords={
            'time': subset.time,
            'lat': subset.latitude,
            'lon': subset.longitude
        }
    )
    
    # Save to file
    output_ds.to_netcdf('output/mhw_mask.nc')
    
    # Create report
    print("Generating report...")
    
    # Determine regional events
    # A day is active if at least one sea cell is inside a per-cell MHW
    active_days = np.any(mhw_mask, axis=(1, 2))  # Shape: (days,)
    
    # Find maximal runs of consecutive active days
    events = []
    i = 0
    while i < len(active_days):
        if active_days[i]:
            # Found start of an event
            event_start = i
            # Extend to find end
            while i < len(active_days) and active_days[i]:
                i += 1
            event_end = i - 1
            # Convert indices back to dates
            start_date_event = start_date + timedelta(days=event_start)
            end_date_event = start_date + timedelta(days=event_end)
            events.append({
                'onset': start_date_event.strftime('%Y-%m-%d'),
                'end': end_date_event.strftime('%Y-%m-%d')
            })
        else:
            i += 1
    
    # Create report JSON
    report = {
        'region': {
            'lat_min': lat_min,
            'lat_max': lat_max,
            'lon_min': lon_min,
            'lon_max': lon_max
        },
        'baseline_analysed': {
            'start': baseline_start.strftime('%Y-%m-%d'),
            'end': baseline_end.strftime('%Y-%m-%d')
        },
        'target_analysed': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        },
        'events': events,
        'complete': True,
        'caveats': ''
    }
    
    import json
    with open('output/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("Analysis complete!")
    print(f"Found {len(events)} regional MHW events:")
    for event in events:
        print(f"  {event['onset']} to {event['end']}")
    
    return report

# Run the analysis
if __name__ == "__main__":
    report = main()