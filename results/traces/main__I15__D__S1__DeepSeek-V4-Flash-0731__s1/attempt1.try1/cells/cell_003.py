
import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
import re
dates = sorted([f.split('sst_')[-1].split('.')[0] for f in files])
print(len(dates))
print(dates[0], dates[-1])
# check for the dates we need
needed_baseline = []
import datetime
# baseline 1992-2002
for y in range(1992, 2003):
    for m in range(1,13):
        for d in range(1,32):
            try:
                dt=datetime.date(y,m,d)
                needed_baseline.append(dt.strftime('%Y%m%d'))
            except: pass
# plus window days
for y in [1991]:
    for m in range(12,13):
        for d in range(27,32):
            try:
                dt=datetime.date(y,m,d)
                needed_baseline.append(dt.strftime('%Y%m%d'))
            except: pass
for y in [2003]:
    for m in range(1,2):
        for d in range(1,6):
            try:
                dt=datetime.date(y,m,d)
                needed_baseline.append(dt.strftime('%Y%m%d'))
            except: pass
# target
for y in [2019]:
    for m in range(6,10):
        for d in range(1,32):
            try:
                dt=datetime.date(y,m,d)
                needed_baseline.append(dt.strftime('%Y%m%d'))
            except: pass
needed = set(needed_baseline)
have = set(dates)
print("missing baseline+target:", sorted(needed - have)[:50], len(needed-have))
print("have sample beyond:", [d for d in sorted(have) if d not in needed][:20])
