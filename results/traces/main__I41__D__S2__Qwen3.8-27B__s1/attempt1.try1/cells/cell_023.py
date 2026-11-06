path = '/work/pipeline.py'
src = open(path).read()
old = "m3 = mask.reshape(92, len(latm), len(lonm))"
new = "m3 = mask.reshape(92, int(latm.sum()), int(lonm.sum()))"
assert old in src
src = src.replace(old, new)
open(path, 'w').write(src)
exec(src)
