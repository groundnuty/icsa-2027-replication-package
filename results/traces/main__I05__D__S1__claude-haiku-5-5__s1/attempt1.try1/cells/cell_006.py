import time
t=time.time()
fs.get(base+'sst_19920101.nc','/work/b.nc')
print(time.time()-t, os.path.getsize('/work/b.nc'))