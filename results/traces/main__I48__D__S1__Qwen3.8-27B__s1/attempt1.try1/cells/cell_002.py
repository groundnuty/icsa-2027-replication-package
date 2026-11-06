import fsspec
fs = fsspec.filesystem('onedata')
names = [p.split('/')[-1] for p in fs.ls('icsa2027_data_20261101T090944Z/s1z')]
names.sort()
print("count:", len(names))
print("first:", names[0], "last:", names[-1])
# any files outside the sst_* pattern?
import re
odd = [n for n in names if not re.fullmatch(r'sst_\d{8}\.nc', n)]
print("odd:", odd[:20])
