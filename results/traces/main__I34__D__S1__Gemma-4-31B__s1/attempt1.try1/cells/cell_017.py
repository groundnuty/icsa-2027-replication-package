import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'

try:
    test_file = f'{path}/sst_20070601.nc'
    print(f"Checking {test_file}...")
    if test_file in fs.ls(path):
        print("Found it!")
    else:
        print("Not in ls(path)")
        # Try getting it anyway
        fs.get(test_file, '/work/test_2007.nc')
        print("Successfully downloaded!")
except Exception as e:
    print(f"Error: {e}")
