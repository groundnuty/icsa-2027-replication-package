import fsspec, re, collections
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
f=fs.find(base); print('find', len(f))
yrs=collections.Counter(re.search(r'sst_(\d{4})',x).group(1) for x in f if re.search(r'sst_(\d{4})',x)); print(sorted(yrs.items()))
print([x for x in f if not re.search(r'sst_\d{8}\.nc$',x)][:5])