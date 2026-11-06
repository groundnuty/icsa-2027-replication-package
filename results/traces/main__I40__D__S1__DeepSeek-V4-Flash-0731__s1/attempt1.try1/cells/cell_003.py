
import fsspec, re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# Extract dates from filenames
dates = []
for f in files:
    m = re.search(r'sst_(\d{4})(\d{2})(\d{2})\.nc$', f)
    if m:
        dates.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
dates.sort()
print(f"First file: {dates[0]}")
print(f"Last file: {dates[-1]}")
print(f"Total: {len(dates)}")
# Show unique years
years = sorted(set(d[0] for d in dates))
print(f"Years: {years}")
# Check per year count
from collections import Counter
year_counts = Counter(d[0] for d in dates)
for y in sorted(year_counts):
    print(f"  {y}: {year_counts[y]} files")
