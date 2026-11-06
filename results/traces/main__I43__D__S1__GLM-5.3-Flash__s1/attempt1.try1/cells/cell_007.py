import fsspec
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
for y in [1991,1992,2002,2003,2017]:
    g = sorted(fs.glob(f'{p}/sst_{y}*.nc'))
    print(y, len(g), g[0].split('/')[-1] if g else '-', g[-1].split('/')[-1] if g else '-')
