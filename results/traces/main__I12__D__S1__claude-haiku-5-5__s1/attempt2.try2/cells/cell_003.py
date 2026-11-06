import fsspec,re,os,collections
fs = fsspec.filesystem('onedata')
allf = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
names=[os.path.basename(f) for f in allf]
print(len(names), names[0], names[-1])
print([n for n in names if not re.match(r'sst_\d{8}\.nc$',n)][:20])
print(sorted(collections.Counter(n[4:8] for n in names).items()))