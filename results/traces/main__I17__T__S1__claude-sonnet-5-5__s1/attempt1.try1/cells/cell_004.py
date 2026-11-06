l=fs.ls(p,detail=False);print(len(l))
try:
    print(fs.exists(p+'/sst_19920101.nc'),fs.exists(p+'/sst_20100831.nc'))
except Exception as e:print(e)