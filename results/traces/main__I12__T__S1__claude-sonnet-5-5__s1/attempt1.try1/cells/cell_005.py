import fsspec,xarray as xr, numpy as np, pandas as pd
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
L=fs.ls(p); print(L[:2])
names=[str(x).split('/')[-1] if isinstance(x,str) else x['name'] for x in L]
s=pd.Series(pd.to_datetime([n[4:12] for n in names if n.startswith('sst_')]))
print(s.min(),s.max(),len(s))
print(s.dt.year.value_counts().sort_index().to_dict())
print([n for n in names if not n.startswith('sst_')])