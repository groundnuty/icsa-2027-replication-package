import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
for f in (lambda: fs.find(p), lambda: fs.glob(p+'/sst_2012*.nc'), lambda: fs.ls(p,detail=False,limit=100000)):
    try:
        r=f();print(len(r),r[-1])
    except Exception as e:print(e)