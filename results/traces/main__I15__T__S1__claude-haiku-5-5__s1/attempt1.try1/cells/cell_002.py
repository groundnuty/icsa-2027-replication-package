
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
import collections,re
print(len(files))
print(collections.Counter(re.sub(r'\d','#',f.split('/')[-1]) for f in files))
print(files[-3:])
