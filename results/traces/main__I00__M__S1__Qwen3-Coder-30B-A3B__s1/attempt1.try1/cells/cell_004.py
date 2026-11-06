import os
import re
from datetime import datetime

# Check what date files exist in the directory
date_pattern = re.compile(r'sst_(\d{8})\.nc')
available_dates = set()

for filename in os.listdir("/data/icsa2027_data_20261101T090944Z/s1z"):
    match = date_pattern.match(filename)
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            available_dates.add(date_obj)
        except ValueError:
            continue

# Check specific periods
target_start = datetime(2004, 6, 1)
target_end = datetime(2004, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Find all available dates in target and baseline periods
target_dates = [d for d in available_dates if target_start <= d <= target_end]
baseline_dates = [d for d in available_dates if baseline_start <= d <= baseline_end]

print(f"Available target dates: {len(target_dates)}")
if target_dates:
    print(f"Target date range: {min(target_dates).strftime('%Y-%m-%d')} to {max(target_dates).strftime('%Y-%m-%d')}")

print(f"Available baseline dates: {len(baseline_dates)}")
if baseline_dates:
    print(f"Baseline date range: {min(baseline_dates).strftime('%Y-%m-%d')} to {max(baseline_dates).strftime('%Y-%m-%d')}")

# Let's see some examples of the data
if target_dates:
    test_date = min(target_dates)
    test_file = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{test_date.strftime('%Y%m%d')}.nc"
    print(f"\nExamining sample file for {test_date}: {test_file}")
    
    try:
        import xarray as xr
        ds = xr.open_dataset(test_file, engine="h5netcdf")
        print("Sample data shape:", ds.analysed_sst.shape)
        print("Latitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
        print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
        ds.close()
    except Exception as e:
        print(f"Error reading file: {e}")