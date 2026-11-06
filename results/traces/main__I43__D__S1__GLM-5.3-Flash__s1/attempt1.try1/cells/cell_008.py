import fsspec, time
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
g = fs.glob(p + '/sst_1992*.nc')
print('glob 1992:', len(g), round(time.time()-t0,2))
g = fs.glob(p + '/sst_2017*.nc')
print('glob 2017:', len(g))
print(fs.exists(p + '/sst_19920601.nc'), fs.exists(p + '/sst_19910930.nc'))
# ls with detail for a nonexistent file?
try:
    print(fs.info(p + '/sst_19911227.nc'))
except Exception as ex:
    print('info err', ex)
