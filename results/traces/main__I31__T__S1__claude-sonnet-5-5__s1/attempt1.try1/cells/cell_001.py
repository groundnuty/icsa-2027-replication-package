import fsspec
fs=fsspec.filesystem('onedata')
for p in ['icsa2027_data_20261101T090944Z/s1z']:
    r=fs.ls(p,detail=False);print(len(r),r[:50])