
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check what files exist in the baseline range
import datetime
def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += datetime.timedelta(days=1)

# Baseline period with windows: 1991-12-27 to 2003-01-05
start = datetime.date(1991, 12, 27)
end = datetime.date(2003, 1, 5)

files_needed = []
missing = []
for d in daterange(start, end):
    fname = f'sst_{d.strftime("%Y%m%d")}.nc'
    fpath = f'{base}/{fname}'
    if fs.exists(fpath):
        files_needed.append(fpath)
    else:
        missing.append(fname)

print(f"Baseline files needed: {len(files_needed)}")
print(f"Missing: {len(missing)}")
if missing:
    print(missing[:10])

# Target files
start_t = datetime.date(2021, 6, 1)
end_t = datetime.date(2021, 8, 31)
target_files = []
missing_t = []
for d in daterange(start_t, end_t):
    fname = f'sst_{d.strftime("%Y%m%d")}.nc'
    fpath = f'{base}/{fname}'
    if fs.exists(fpath):
        target_files.append(fpath)
    else:
        missing_t.append(fname)

print(f"Target files needed: {len(target_files)}")
print(f"Missing: {len(missing_t)}")
if missing_t:
    print(missing_t)
