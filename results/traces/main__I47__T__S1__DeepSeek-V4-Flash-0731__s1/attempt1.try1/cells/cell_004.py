
import fsspec
fs = fsspec.filesystem('onedata')
# Look at parent dirs
print(fs.ls('icsa2027_data_20261101T090944Z'))
print(fs.ls('/'))
