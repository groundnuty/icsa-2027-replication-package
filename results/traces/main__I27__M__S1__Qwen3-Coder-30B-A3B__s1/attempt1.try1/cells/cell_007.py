import os

# Check what years of data are available
print("Available files in s1z directory:")
files = []
for root, dirs, filenames in os.walk("/data/icsa2027_data_20261101T090944Z/s1z"):
    for filename in filenames:
        if filename.startswith('sst_') and filename.endswith('.nc'):
            files.append(filename)
    break

# Sort files by date
files.sort()

print(f"Total files: {len(files)}")
print("First 10 files:")
for f in files[:10]:
    print(f"  {f}")

print("Last 10 files:")
for f in files[-10:]:
    print(f"  {f}")

# Check what years are available
years = set()
for f in files:
    year = f.split('_')[1][:4]
    years.add(year)

print(f"\nYears available: {sorted(years)}")