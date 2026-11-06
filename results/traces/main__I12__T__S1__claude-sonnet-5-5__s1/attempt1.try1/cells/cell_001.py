import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
def ls(p):
    for x in fs.ls(p): print(x)
ls(p)