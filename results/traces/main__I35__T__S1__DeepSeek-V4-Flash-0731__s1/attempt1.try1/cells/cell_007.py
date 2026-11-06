
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Try to access a file from 1992
try:
    f = fs.open(f'{base}/sst_19920101.nc', 'rb')
    print("19920101 exists")
    print(f)
except Exception as e:
    print(f"19920101: {e}")

# Try to access a file from 2009
try:
    f = fs.open(f'{base}/sst_20090601.nc', 'rb')
    print("20090601 exists")
except Exception as e:
    print(f"20090601: {e}")
