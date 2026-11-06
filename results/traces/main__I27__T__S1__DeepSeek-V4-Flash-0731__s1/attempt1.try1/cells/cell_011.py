
import fsspec
fs = fsspec.filesystem('onedata')
# Let's try to list all files by checking individual years
import re

# Try to list with a different method
# Let me try using find
try:
    result = fs.find('icsa2027_data_20261101T090944Z/s1z')
    print("Find results:", len(result))
except Exception as e:
    print("Find error:", e)

# Try walking
try:
    for root, dirs, files in fs.walk('icsa2027_data_20261101T090944Z/s1z'):
        print(f"Root: {root}, # files: {len(files)}")
        break
except Exception as e:
    print("Walk error:", e)
