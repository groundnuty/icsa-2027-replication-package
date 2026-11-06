import fsspec, inspect
fs = fsspec.filesystem('onedata')
print(inspect.signature(fs.ls))
print(type(fs).__mro__)
# try find
try:
    fnd = fs.find('icsa2027_data_20261101T090944Z/s1z', detail=False)
    print('find n', len(fnd), fnd[0], fnd[-1])
except Exception as e:
    print('find fail', type(e).__name__, str(e)[:200])
