import fsspec, time
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
g = fs.glob(p + '/sst_1982*.nc')
print('glob 1982:', len(g), round(time.time()-t0,2),'s')
t0=time.time()
g = fs.glob(p + '/sst_1992*.nc')
print('glob 1992:', len(g), round(time.time()-t0,2),'s')
t0=time.time()
cnt = 0
for i in range(50):
    if fs.exists(p + '/sst_1992%02d01.nc' % (i%12+1)): cnt+=1
print('50 exists:', round(time.time()-t0,2),'s, found', cnt)
t0=time.time()
g = fs.glob(p + '/sst_19*.nc')
print('glob 19xx:', len(g), round(time.time()-t0,2),'s')
