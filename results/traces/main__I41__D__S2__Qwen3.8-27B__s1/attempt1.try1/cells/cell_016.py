path = '/work/pipeline.py'
src = open(path).read()
src = src.replace("y = (dates.astype('datetime64[Y]')).astype('int64')",
                  "y = (dates.astype('datetime64[Y]')).astype('int64') + 1970")
src = src.replace("assert T == 4093, T", "assert T == 4028, T")
open(path, 'w').write(src)
print("patched")
