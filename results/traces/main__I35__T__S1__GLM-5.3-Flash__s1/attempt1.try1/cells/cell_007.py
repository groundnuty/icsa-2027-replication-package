import fsspec, time
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
try:
    more = fs.ls(base, start_from=999)
    print('start_from OK n=', len(more), 'time', round(time.time()-t0,2))
    print(more[0].split('/')[-1], more[-1].split('/')[-1])
except Exception as ex:
    print('start_from err', repr(ex)[:300])
