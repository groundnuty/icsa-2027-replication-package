import fsspec
fs = fsspec.filesystem('onedata')
for p in ['sst_1992','sst_2008','sst_1991','sst_2003']:
    print(p, len(fs.glob(f'icsa2027_data_20261101T090944Z/s1z/{p}*.nc')))
print(fs.ls('icsa2027_data_20261101T090944Z/s2z', detail=False)[:5])
print(len(fs.ls('icsa2027_data_20261101T090944Z/s2z', detail=False)))