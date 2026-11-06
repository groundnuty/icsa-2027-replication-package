import re
names=set(os.path.basename(f) for f in fl)
for pat in ['sst_19920101.nc','sst_20130601.nc','sst_20021231.nc']:print(pat,pat in names, fs.exists(p+'/'+pat))
try:
    r=fs.ls(p,detail=False,offset=1000);print(len(r))
except Exception as e:print(e)
print(fs.ls(p+'/..',detail=False)[:20])