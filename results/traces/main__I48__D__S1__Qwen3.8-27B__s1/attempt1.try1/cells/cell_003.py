import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# check for subdirectories via walk (limit depth)
import itertools
dirs = set()
files = 0
# ls with detail
d = fs.ls(base, detail=True)
print("ls detail len:", len(d))
print("sample detail:", d[0])
# Try find with maxdepth
res = fs.find(base, maxdepth=1)
print("find maxdepth1 len:", len(res))
# Try walk
walked = list(itertools.islice(fs.walk(base), 5))
for w in walked:
    print(w[0], len(w[1]))
