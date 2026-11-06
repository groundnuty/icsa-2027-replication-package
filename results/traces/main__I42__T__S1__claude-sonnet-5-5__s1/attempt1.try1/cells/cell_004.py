for f in (lambda: fs.find(p), lambda: fs.glob(p+'/sst_2012*.nc'), lambda: fs.ls(p,detail=False,limit=100000)):
    try:
        r=f();print(len(r))
    except Exception as e:print(e)