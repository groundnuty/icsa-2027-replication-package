import fsspec
fs = fsspec.filesystem('onedata')
# explore top-level
for p in ['/', '~']:
    try:
        print(p, fs.ls(p))
    except Exception as e:
        print(p, "ERR", e)
