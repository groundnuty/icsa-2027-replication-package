import fsspec
fs = fsspec.filesystem('onedata')
# Try to list the root or find the file
for path in ['/', '/icsa2027_data_20261101T090944Z', '/icsa2027_data_20261101T090944Z/s2z']:
    try:
        entries = fs.ls(path, detail=False)
        print(path, '->', entries[:20])
    except Exception as e:
        print(path, 'ERR', type(e).__name__, e)
