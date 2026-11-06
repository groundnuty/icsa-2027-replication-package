import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
for n in ['sst_19920101.nc','sst_20210601.nc','sst_19840927.nc']:print(fs.exists(p+'/'+n))
print(fs.ls('icsa2027_data_20261101T090944Z',detail=False))