
import fsspec
fs = fsspec.filesystem('onedata')
# Try ls with details
result = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=True)
print(len(result))
# Check the signature of ls
import inspect
print(inspect.signature(fs.ls))
