import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# glob for needed periods
import numpy as np
def glob_count(pat):
    r = fs.glob(f"{base}/{pat}")
    return len(r), (sorted(r)[0].split('/')[-1] if r else None), (sorted(r)[-1].split('/')[-1] if r else None)
print(glob_count('sst_1992*.nc'))
print(glob_count('sst_1993*.nc'))
print(glob_count('sst_2002*.nc'))
print(glob_count('sst_2003*.nc'))
print(glob_count('sst_2021*.nc'))
print(glob_count('sst_1991*.nc'))
print(glob_count('sst_*.nc'))
