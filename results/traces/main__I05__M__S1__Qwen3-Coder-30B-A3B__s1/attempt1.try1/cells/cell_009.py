import os
from datetime import datetime

# Let's examine the file naming pattern
base_path = "/data/icsa2027_data_20261101T090944Z/s1z"

# Get all files and sort them by date
files = []
for filename in os.listdir(base_path):
    if filename.startswith('sst_') and filename.endswith('.nc'):
        try:
            # Extract date from filename (format sst_YYYYMMDD.nc)
            date_str = filename[4:12]  # sst_YYYYMMDD.nc -> YYYYMMDD
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            files.append((filename, date_obj))
        except:
            continue

# Sort by date
files.sort(key=lambda x: x[1])

print("First 10 files:")
for filename, date in files[:10]:
    print(f"  {filename} ({date.strftime('%Y-%m-%d')})")

print("\nLast 10 files:")
for filename, date in files[-10:]:
    print(f"  {filename} ({date.strftime('%Y-%m-%d')})")

# Find files in our target period
target_files = [f for f in files if START_DATE <= f[1] <= END_DATE]
print(f"\nFiles in target period ({START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}):")
for filename, date in target_files[:5]:  # Show first 5
    print(f"  {filename} ({date.strftime('%Y-%m-%d')})")
    
# Find files in baseline period  
baseline_files = [f for f in files if BASELINE_START <= f[1] <= BASELINE_END]
print(f"\nFiles in baseline period ({BASELINE_START.strftime('%Y-%m-%d')} to {BASELINE_END.strftime('%Y-%m-%d')}):")
for filename, date in baseline_files[:5]:  # Show first 5
    print(f"  {filename} ({date.strftime('%Y-%m-%d')})")