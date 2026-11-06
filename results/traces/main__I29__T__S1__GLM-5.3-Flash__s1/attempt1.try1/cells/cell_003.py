import fsspec
fs = fsspec.filesystem('onedata')
g = fs.glob('icsa2027_data_20261101T090944Z/s1z/*.nc')
print(len(g))
print(g[0], g[-1])
