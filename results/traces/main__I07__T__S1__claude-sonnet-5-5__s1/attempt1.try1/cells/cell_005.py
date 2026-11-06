import fsspec,re,pandas as pd
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
names=fs.ls(p,detail=False);print(len(names),len(set(names)))
names=sorted(set(names));print(names[0],names[-1])
d=pd.to_datetime([re.search(r'(\d{8})',f).group(1) for f in names],format='%Y%m%d')
print(d.is_unique,len(d))
print([n for n in names if not re.search(r'sst_\d{8}\.nc$',n)])