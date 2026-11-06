import fsspec, re
fs = fsspec.filesystem('onedata')
ls = fs.ls('icsa2027_data_20261101T090944Z/s2z')
print('total files in s2z:', len(ls))
print('first:', ls[0])
print('last:', ls[-1])
dates = sorted(p.split('/')[-1] for p in ls)
print(dates[:5], dates[-5:])
weird = [p for p in dates if not re.search(r'sst_\d{8}\.nc$', p)]
print('weird:', weird[:20])
d8 = sorted(p[4:12] for p in dates if re.search(r'sst_\d{8}\.nc$', p))
print('range:', d8[0], d8[-1], 'n:', len(set(d8)))
