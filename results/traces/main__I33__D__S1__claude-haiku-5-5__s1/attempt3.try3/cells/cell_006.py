import fsspec
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
for p in ['sst_19921231.nc','sst_19920101.nc','sst_20140601.nc','sst_19840926.nc','sst_19840927.nc']:
    print(p, fs.exists(f'{base}/{p}'))
g=fs.glob(f'{base}/sst_1992*'); print('glob1992',len(g))
g=fs.glob(f'{base}/sst_2014*'); print('glob2014',len(g))