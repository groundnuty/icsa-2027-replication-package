import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
for pat in [base+'/sst_2019*', base+'/sst_1992*', base+'/sst_2003*']:
    g=fs.glob(pat); print(pat,len(g), g[:2], g[-1:] if g else '')
f=fs.find(base); print('find',len(f))