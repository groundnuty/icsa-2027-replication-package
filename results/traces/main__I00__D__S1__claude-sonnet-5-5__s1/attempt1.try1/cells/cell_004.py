r=fs.ls(p,detail=False);print(len(r))
try:
    print(len(fs.find(p)))
except Exception as e:print(e)
print(fs.exists(f"{p}/sst_20040601.nc"),fs.exists(f"{p}/sst_19950101.nc"),fs.exists(f"{p}/sst_20040831.nc"))