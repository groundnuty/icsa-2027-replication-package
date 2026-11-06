import re,os
allf = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(allf))
names=[os.path.basename(f) for f in allf]
print([n for n in names if not re.match(r'sst_\d{8}\.nc$',n)][:20])
print(names[0], names[-1])
import collections
print(collections.Counter(n[4:8] for n in names))