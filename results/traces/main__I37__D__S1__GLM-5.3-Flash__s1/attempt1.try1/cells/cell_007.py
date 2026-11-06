import fsspec, inspect
fs = fsspec.filesystem('onedata')
print(type(fs))
print(inspect.signature(fs.ls))
print(inspect.signature(fs._ls) if hasattr(fs,'_ls') else 'no _ls')
# try ls with different args
try:
    e = fs.ls('icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc', detail=False)
    print("ls single file:", e)
except Exception as ex:
    print("err", ex)
print([a for a in dir(fs) if 'pag' in a.lower() or 'limit' in a.lower() or 'token' in a.lower()])
