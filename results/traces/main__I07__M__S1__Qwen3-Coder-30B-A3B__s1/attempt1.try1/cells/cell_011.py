import os

# Check the exact file structure
path_s1z = "/data/icsa2027_data_20261101T090944Z/s1z"
files = sorted(os.listdir(path_s1z))[:10]  # First 10 files

print("First 10 filenames:")
for f in files:
    print(f"'{f}'")

print("\nChecking file patterns:")
for f in files:
    if f.startswith("sst_") and f.endswith(".nc"):
        date_part = f[4:-3]  # Remove "sst_" prefix and ".nc" suffix
        print(f"File: {f}, Date part: {date_part}")
        if len(date_part) == 8:
            try:
                year = int(date_part[:4])
                month = int(date_part[4:6])  
                day = int(date_part[6:8])
                print(f"  Parsed date: {year}-{month:02d}-{day:02d}")
            except:
                print(f"  Could not parse date")