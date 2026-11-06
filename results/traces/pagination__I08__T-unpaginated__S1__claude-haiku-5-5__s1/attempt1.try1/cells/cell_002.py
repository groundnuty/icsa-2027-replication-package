import re, collections
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(files))
cnt = collections.Counter()
other=[]
for f in files:
    m = re.search(r'(\d{8})\.nc$', f)
    if m: cnt[m.group(1)[:4]]+=1
    else: other.append(f)
print(sorted(cnt.items())); print(other[:20], len(other))
