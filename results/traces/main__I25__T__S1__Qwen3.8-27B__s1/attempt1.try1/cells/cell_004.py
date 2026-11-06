
import fsspec, datetime as dt, time
fs = fsspec.filesystem('onedata')
roots = list(fs.walk('/icsa2027_data_20261101T090944Z/s1z'))
print("num roots:", len(roots))
for r in roots[:10]:
    print(r[0], "dirs:", len(r[1]), "files:", len(r[2]))
# check info of the dir itself
print(fs.info('/icsa2027_data_20261101T090944Z/s1z'))
# maybe parent has more
print(fs.ls('/icsa2027_data_20261101T090944Z'))
