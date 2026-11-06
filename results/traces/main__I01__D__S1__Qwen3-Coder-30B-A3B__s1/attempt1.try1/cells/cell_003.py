# Check what years are available in the dataset
import glob
import re

# Get all files and extract dates
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
dates = []
for f in files:
    match = re.search(r'sst_(\d{8})\.nc', f)
    if match:
        dates.append(match.group(1))

dates.sort()
print("Available date range:", dates[0], "to", dates[-1])

# Let's check a few more files to see the pattern
print("First 10 files:")
for i in range(min(10, len(dates))):
    print(dates[i])