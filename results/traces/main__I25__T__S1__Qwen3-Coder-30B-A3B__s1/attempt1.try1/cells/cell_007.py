import fsspec
import re
from datetime import datetime

fs = fsspec.filesystem('onedata')

# Check s2z directory
try:
    s2z_files = fs.ls('/icsa2027_data_20261101T090944Z/s2z')
    print("s2z directory contents (first 10):")
    for f in s2z_files[:10]:
        print(f)
        
    # Extract dates from s2z files
    date_pattern = re.compile(r'sst_(\d{8})\.nc')
    s2z_dates = []
    
    for f in s2z_files:
        match = date_pattern.search(f)
        if match:
            date_str = match.group(1)
            try:
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                s2z_dates.append((date_obj, f))
            except ValueError:
                continue
    
    if s2z_dates:
        s2z_dates.sort()
        print(f"\ns2z date range: {s2z_dates[0][0].strftime('%Y-%m-%d')} to {s2z_dates[-1][0].strftime('%Y-%m-%d')}")
    else:
        print("\nNo valid dates found in s2z directory")
        
except Exception as e:
    print(f"Error accessing s2z: {e}")