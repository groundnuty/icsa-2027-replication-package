import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
entries = fs.ls(base)
print("n files:", len(entries))
names = [e.split('/')[-1] for e in entries]
print("first:", names[0], "last:", names[-1])
# find range
import re
dates = [n[4:12] for n in names if n.startswith('sst_')]
print("date range:", min(dates), max(dates))
# check for non-standard names
others = [n for n in names if not re.fullmatch(r'sst_\d{8}\.nc', n)]
print("nonstandard names:", others[:20], len(others))
