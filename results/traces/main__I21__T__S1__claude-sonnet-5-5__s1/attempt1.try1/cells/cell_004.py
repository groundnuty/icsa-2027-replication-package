print(fs.ls(p+'/..',detail=False)[:20])
r=fs.ls(p,detail=False);print(len(r))
for n in ['sst_19920101.nc','sst_20210601.nc']:print(fs.exists(p+'/'+n))