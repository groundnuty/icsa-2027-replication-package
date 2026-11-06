import fsspec
fs = fsspec.filesystem('onedata')
base = "icsa2027_data_20261101T090944Z"
try:
    print("parent ls:", fs.ls(base, detail=False))
except Exception as e:
    print("err:", e)
# check find on s1z
try:
    found = fs.find(base + "/s1z")
    print("find count:", len(found))
except Exception as e:
    print("find err:", e)