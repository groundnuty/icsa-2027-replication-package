import fsspec
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
det = fs.ls(p, detail=True)
print('n entries', len(det))
types = {}
for d in det: types[d.get('type')] = types.get(d.get('type'),0)+1
print(types)
names = [d['name'] for d in det if d.get('type')=='file']
import re
print('first', names[0], 'last', names[-1])
# check subdirectories?
dirs = [d['name'] for d in det if d.get('type')!='file']
print('non-file entries:', dirs[:10], 'count', len(dirs))
# check name pattern
pat = re.compile(r'^sst_(\d{8})\.nc$')
dates = []
bad = [n for n in names if not pat.match(n)]
print('bad names', bad[:5], len(bad))
dates = [pat.match(n).group(1) for n in names if pat.match(n)]
print('n dates', len(dates), 'min', min(dates), 'max', max(dates))
