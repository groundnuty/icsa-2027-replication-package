
import fsspec
fs = fsspec.filesystem('onedata')
print(fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)[:200])
