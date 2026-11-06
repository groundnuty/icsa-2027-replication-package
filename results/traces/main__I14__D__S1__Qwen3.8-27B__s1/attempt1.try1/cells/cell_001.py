import fsspec, os
fs = fsspec.filesystem('onedata')
base = "icsa2027_data_20261101T090944Z/s1z"
try:
    files = fs.ls(base, detail=True)
except Exception as e:
    files = str(e)
print(files if isinstance(files, str) else [(f['name'], f.get('size'), f.get('isdir')) for f in files])