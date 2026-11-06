
import os
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(f"Total files: {len(files)}")
print(f"First 5: {files[:5]}")
print(f"Last 5: {files[-5:]}")
# Check which years are present
years = set()
for f in files:
    if f.startswith('sst_'):
        years.add(f[4:8])
print(f"Years: {sorted(years)}")
