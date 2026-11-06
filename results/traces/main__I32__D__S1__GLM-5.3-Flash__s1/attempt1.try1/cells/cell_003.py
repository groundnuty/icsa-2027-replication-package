import fsspec
fs = fsspec.filesystem('onedata')
parent = fs.ls('icsa2027_data_20261101T090944Z')
print("parent:", parent)
# test glob for specific dates
for pat in ['icsa2027_data_20261101T090944Z/s1z/sst_1992*.nc',
            'icsa2027_data_20261101T090944Z/s1z/sst_2005*.nc',
            'icsa2027_data_20261101T090944Z/s1z/sst_2003*.nc']:
    g = fs.glob(pat)
    print(pat, len(g), g[:2], g[-2:] if g else '')
