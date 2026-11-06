import fsspec
from datetime import datetime

fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')

print("First 10 filenames:")
for i, f in enumerate(files[:10]):
    print(f"{i}: {f}")

# Try to parse one filename to make sure the pattern works
test_file = files[0]
parts = test_file.split('_')
print(f"\nTest file parts: {parts}")
if len(parts) >= 2:
    date_part = parts[1]
    print(f"Date part: {date_part}")
    try:
        date_obj = datetime.strptime(date_part, '%Y%m%d')
        print(f"Parsed date: {date_obj}")
    except ValueError as e:
        print(f"Error parsing date: {e}")