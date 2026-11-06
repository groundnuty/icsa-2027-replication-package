
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check what years we can access by trying
import datetime

# Try checking if a few specific files exist
test_dates = [
    '19911227', '19911231', '19920101', '19921231',
    '19950101', '19991231', '20020101', '20021231',
    '20030101', '20030105', '20090601', '20090831'
]
for d in test_dates:
    try:
        f = fs.open(f'{base}/sst_{d}.nc', 'rb')
        print(f"{d}: exists")
        f.close()
    except Exception as e:
        print(f"{d}: {e}")
