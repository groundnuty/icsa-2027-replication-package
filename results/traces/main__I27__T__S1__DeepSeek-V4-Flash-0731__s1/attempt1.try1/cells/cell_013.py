
import fsspec
fs = fsspec.filesystem('onedata')
# Try to use the underlying client to list all files
# Let's check if there's a way to paginate
# First, let's try to directly check which files exist for specific dates

# Let me just check the specific files I need by probing
# For the target period 2008-06-01 to 2008-08-31
# And baseline 1992-2002 (with ±5 day extensions)

# Let me try checking a bunch of files
import datetime

def check_file(date_str):
    path = f'icsa2027_data_20261101T090944Z/s1z/sst_{date_str}.nc'
    try:
        info = fs.info(path)
        return True
    except:
        return False

# Check target files
for d in range(1, 4):
    print(f"200806{d:02d}: {check_file(f'200806{d:02d}')}")

# Check baseline files  
print(f"19920101: {check_file('19920101')}")
print(f"20021231: {check_file('20021231')}")
print(f"19911227: {check_file('19911227')}")
print(f"20030105: {check_file('20030105')}")
print(f"19820101: {check_file('19820101')}")
print(f"19841231: {check_file('19841231')}")
