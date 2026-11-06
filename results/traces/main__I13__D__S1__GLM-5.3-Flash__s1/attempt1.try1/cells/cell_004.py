import fsspec
from onedatafilerestclient.errors import OnedataRESTError
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
try:
    attrs = fs.info(base)
    print(attrs)
except Exception as e:
    print('info err:', e)
