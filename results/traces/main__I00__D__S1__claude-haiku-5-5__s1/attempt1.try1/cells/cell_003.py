import fsspec, re, os
fs = fsspec.filesystem('onedata')
allf = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[f.split('/')[-1] for f in allf]
print(len(names))
odd=[n for n in names if not re.fullmatch(r'sst_\d{8}\.nc',n)]
print(odd[:20], len(odd))
print(names[0], names[-1])