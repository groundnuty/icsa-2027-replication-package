import fsspec, re, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
allnames = []
marker = None
entries = fs.ls(base, detail=False)
print('first listing size:', len(entries))
allnames += entries
# Try to detect pagination
try:
    entries2 = fs.ls(base, detail=False, marker=entries[-1])
    print('marker listing size:', len(entries2))
    print('first of entries2:', entries2[0])
except TypeError as te:
    print('marker not supported:', te)
except Exception as e:
    print('marker err:', type(e).__name__, e)
