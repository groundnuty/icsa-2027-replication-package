import fsspec

# Get all files in the directory
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')

print("First 10 files:")
for i, f in enumerate(files[:10]):
    print(f"{i}: {f}")

print("\nChecking file pattern...")
for f in files[:5]:
    parts = f.split('/')
    filename = parts[-1]  # Get just the filename
    print(f"Full path: {f}")
    print(f"Filename: {filename}")
    if filename.startswith('sst_') and filename.endswith('.nc'):
        date_part = filename.split('_')[1].split('.')[0]
        print(f"  Date part: {date_part}")
        try:
            year = int(date_part[:4])
            print(f"  Year: {year}")
        except Exception as e:
            print(f"  Error parsing year: {e}")