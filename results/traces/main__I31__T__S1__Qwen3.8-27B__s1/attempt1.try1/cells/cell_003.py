
import fsspec, re
fs = fsspec.filesystem('onedata')
entries = fs.ls('/icsa2027_data_20261101T090944Z/s1z', detail=True)
print("num entries:", len(entries))
types = {}
for e in entries[:5]:
    print(e)
# breakdown by first characters
pat = re.compile(r'sst_(\d{8})\.nc$')
import collections
years = collections.Counter()
nonmatch = []
for e in entries:
    name = e['name'] if isinstance(e, dict) else e
    m = pat.match(name.split('/')[-1])
    if m:
        years[int(m.group(1)[:4])] += 1
    else:
        nonmatch.append(name)
print("years:", dict(sorted(years.items())))
print("non-matching:", nonmatch[:20], "count:", len(nonmatch))
