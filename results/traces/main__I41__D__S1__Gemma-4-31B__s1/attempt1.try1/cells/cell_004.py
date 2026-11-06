import fsspec

fs = fsspec.filesystem('onedata')
remote_root = 'icsa2027_data_20261101T090944Z'
contents = fs.ls(remote_root)
for item in contents:
    print(item)
