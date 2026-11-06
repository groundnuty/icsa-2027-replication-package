
import fsspec
fs = fsspec.filesystem('onedata')
# Try to check if files exist for other years in s1z
for date in ['19920101', '20000101', '20080601']:
    path = f'icsa2027_data_20261101T090944Z/s1z/sst_{date}.nc'
    try:
        info = fs.info(path)
        print(f"Found: {path}, size={info['size']}")
    except Exception as e:
        print(f"Not found: {path}: {e}")
