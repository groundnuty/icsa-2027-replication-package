import fsspec
fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s2z'
files = fs.ls(remote_dir)
print(files[:20])
print(f"Total files in s2z: {len(files)}")
