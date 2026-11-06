
import fsspec
fs = fsspec.filesystem('onedata')
# list with details to see sizes
out = fs.ls('/icsa2027_data_20261101T090944Z/s1z', detail=True)
print(type(out), len(out))
print(out[:2])
print(out[-2:])
