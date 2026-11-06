
import fsspec, re
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
# ls may have a limit. Let me try listing with different methods
print(type(files), len(files))
# Try to find files for target period
import fnmatch
# Search for files 2010
pat = 'icsa2027_data_20261101T090944Z/s1z/sst_2010*'
try:
    res = fs.glob(pat)
    print("glob 2010:", len(res))
except Exception as e:
    print("glob error", e)
