import fsspec

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(remote_dir)
sst_files = [f for f in files if 'sst' in f.lower()]
print(f"Files containing 'sst': {len(sst_files)}")
for f in sst_files[:20]:
    print(f)
