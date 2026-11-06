import fsspec, os
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
items = fs.ls(base)
names = sorted([os.path.basename(x) for x in items])
print("total files:", len(names))
print("first:", names[:3], "last:", names[-3:])
# check existence of specific files
import re
def name_for(y,m,d):
    return f"sst_{y:04d}{m:02d}{d:02d}.nc"
setnames = set(names)
for f in [name_for(1991,12,27), name_for(1991,12,31), name_for(1992,1,1), name_for(2002,12,31), name_for(2003,1,5),
          name_for(2021,6,1), name_for(2021,8,31)]:
    print(f, f in setnames)
# find min and max date present
dates = []
for n in names:
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', n)
    if m:
        dates.append(int(m.group(1))*10000+int(m.group(2))*100+int(m.group(3)))
print("date range present:", min(dates), max(dates))
