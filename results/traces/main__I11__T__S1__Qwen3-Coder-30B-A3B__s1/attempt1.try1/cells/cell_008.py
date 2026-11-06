import fsspec
from datetime import datetime
import re

fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')

print("First 10 filenames:")
for i, f in enumerate(files[:10]):
    print(f"{i}: {f}")

# Extract date properly from the path
def extract_date_from_path(filepath):
    # Pattern to match date in sst_YYYYMMDD.nc format
    match = re.search(r'sst_(\d{8})\.nc', filepath)
    if match:
        date_str = match.group(1)
        return datetime.strptime(date_str, '%Y%m%d')
    return None

# Test on first few files
dates = []
for f in files[:20]:  # Check first 20 files
    date = extract_date_from_path(f)
    if date:
        dates.append(date)

dates.sort()
print(f"\nSample dates (first 10):")
for d in dates[:10]:
    print(d)

if dates:
    print(f"\nDate range in dataset: {dates[0]} to {dates[-1]}")
    print(f"Total files: {len(dates)}")
    
    # Check baseline period
    baseline_start = datetime(1992, 1, 1)
    baseline_end = datetime(2002, 12, 31)
    
    in_baseline_range = [d for d in dates if baseline_start <= d <= baseline_end]
    print(f"Files in baseline range (1992-2002): {len(in_baseline_range)}")
    if in_baseline_range:
        print(f"Baseline date range: {min(in_baseline_range)} to {max(in_baseline_range)}")