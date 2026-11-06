import fsspec
fs = fsspec.filesystem('onedata')
# List top-level
try:
    print(fs.ls("", detail=False)[:20])
except Exception as e:
    print("ls error:", e)
