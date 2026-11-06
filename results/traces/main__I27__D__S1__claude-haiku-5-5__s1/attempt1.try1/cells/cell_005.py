import fsspec, re
fs = fsspec.filesystem('onedata')
g = fs.glob('icsa2027_data_20261101T090944Z/s1z/sst_*.nc')
print(len(g), g[0], g[-1])
print(fs.ls('icsa2027_data_20261101T090944Z', detail=False))