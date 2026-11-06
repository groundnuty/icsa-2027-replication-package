
import fsspec
import os

fs = fsspec.filesystem('onedata')
# List the directory structure
print(fs.ls('icsa2027_data_20261101T090944Z/s2z'))
