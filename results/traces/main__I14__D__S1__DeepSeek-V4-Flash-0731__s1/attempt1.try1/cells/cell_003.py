
import fsspec
fs = fsspec.filesystem('onedata')

files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")

# Extract years from filenames
import re
years = set()
for f in files:
    m = re.search(r'sst_(\d{4})', f)
    if m:
        years.add(int(m.group(1)))

print(f"Years present: {sorted(years)}")

# Check what files exist for each year
for y in sorted(years):
    yfiles = [f for f in files if f'sst_{y}' in f]
    print(f"Year {y}: {len(yfiles)} files")
