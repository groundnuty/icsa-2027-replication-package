
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z/'
# List files to see full range
import re
files = fs.ls(base)
names = sorted(set(os.path.basename(f) for f in files)) if False else None
import os
names = sorted(set(os.path.basename(f) for f in files))
print(len(names))
print(names[:3], names[-3:])
# check for gaps: count expected days
import datetime
d0 = datetime.date(1982,1,1)
d1 = datetime.date.fromisoformat(names[-1][4:12])
print("first", names[0], "last", names[-1])
expected = (d1 - d0).days + 1
print("expected days", expected, "have", len(names))
