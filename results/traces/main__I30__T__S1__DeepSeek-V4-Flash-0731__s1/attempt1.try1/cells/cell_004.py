
import fsspec, re
fs = fsspec.filesystem('onedata')
# check if there are other paths or listing options
# Let me check the parent directory
print(fs.ls('icsa2027_data_20261101T090944Z'))
