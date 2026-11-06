files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
import collections, re
names=[f.split('/')[-1] for f in files]
print(len(files), names[:2], names[-3:])
nonstd=[n for n in names if not re.match(r'sst_\d{8}\.nc$',n)]
print(len(nonstd), nonstd[:20])
dates=sorted(re.findall(r'sst_(\d{8})\.nc',' '.join(names)))
print(dates[0], dates[-1], len(dates))