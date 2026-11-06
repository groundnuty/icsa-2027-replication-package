import fsspec
fs = fsspec.filesystem('onedata')
try:
    lst = fs.ls('/')
    print(lst)
except Exception as e:
    print("ERR:", e)
