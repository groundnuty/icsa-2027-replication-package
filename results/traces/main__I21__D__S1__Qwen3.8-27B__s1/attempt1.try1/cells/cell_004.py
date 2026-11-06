import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# Maybe ls is capped at 1000. Try find or walk
try:
    it = fs.find(base)
    lst = list(it)
    print("find count:", len(lst))
except Exception as e:
    print("find error:", e)
    # try walk
    n=0
    for root, dirs, files in fs.walk(base):
        n += len(files)
        if n > 5000: break
    print("walk count (capped):", n)
