
import fsspec
fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s1z"
try:
    ls = fs.ls(path)
    for f in ls[:100]:
        print(f)
except Exception as e:
    print("ERR", e)
