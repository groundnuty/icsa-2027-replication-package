import fsspec
fs = fsspec.filesystem('onedata')
g = fs.glob('icsa2027_data_20261101T090944Z/s1z/sst_2015*.nc')
print(len(g), g[0] if g else None, g[-1] if g else None)
g92 = fs.glob('icsa2027_data_20261101T090944Z/s1z/sst_1992*.nc')
print(len(g92), g92[0] if g92 else None, g92[-1] if g92 else None)
