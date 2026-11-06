import os
from collections import defaultdict

# Check what years are available
path_s1z = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(path_s1z))

year_count = defaultdict(int)
for f in files:
    if f.startswith("sst_"):
        year_str = f[4:8]
        if year_str.isdigit():
            year_count[year_str] += 1

print("Available years:")
for year in sorted(year_count.keys()):
    print(f"{year}: {year_count[year]} files")

# Show the date range
print(f"\nDate range: {min(year_count.keys())} to {max(year_count.keys())}")