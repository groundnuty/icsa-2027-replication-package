import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
# check year coverage via Jan 1 files
for y in range(1982, 2020):
    p = f'{base}sst_{y}0101.nc'
    print(y, fs.exists(p))
