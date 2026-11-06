import fsspec
import os
from datetime import datetime

# Let's try a different approach to list files
fs = fsspec.filesystem('onedata')
base_path = '/icsa2027_data_20261101T090944Z/s1z'

try:
    files = fs.ls(base_path)
    print(f"Found {len(files)} files")
    
    # Get just the first few to see pattern
    for i, file in enumerate(files[:5]):
        print(f"  {file}")
        
    # Try to extract dates from filenames
    dates = []
    for file in files[:10]:
        filename = os.path.basename(file)
        if filename.startswith('sst_') and len(filename) >= 13:
            date_str = filename[4:12]  # Extract YYYYMMDD part
            try:
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                dates.append(date_obj)
            except ValueError:
                continue
    
    if dates:
        print("Sample dates:", sorted(dates)[:5])
        print("Date range:", min(dates), "to", max(dates))
    else:
        print("Could not extract dates")
        
except Exception as e:
    print(f"Error: {e}")