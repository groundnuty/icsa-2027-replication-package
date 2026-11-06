import fsspec, inspect
fs = fsspec.filesystem('onedata')
# fsspec listing APIs to try
for meth in ['ls','find','glob','du','walk']:
    pass
# try find with depth / listing in chunks via ls on subpaths (files -> error)
# Try ls with detail=False to see raw names
e = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
print(len(e), e[:3], e[-1])
# check if fs has a listing pagination parameter via __signature__ tricks
import onedatarestfsspec
print([n for n in dir(onedatarestfsspec) if not n.startswith('_')])
