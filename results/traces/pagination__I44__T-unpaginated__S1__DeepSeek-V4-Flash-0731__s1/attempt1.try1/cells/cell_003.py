import fsspec

fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")

# Extract dates from filenames
import re
dates = []
for f in files:
    m = re.search(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))

dates.sort()
print(f"First: {dates[0]}, Last: {dates[-1]}")
print(f"Total: {len(dates)}")
print("First 10:", dates[:10])
print("Last 10:", dates[-10:])

# Check what years are available
years = set(d[:4] for d in dates)
print("Years:", sorted(years))
