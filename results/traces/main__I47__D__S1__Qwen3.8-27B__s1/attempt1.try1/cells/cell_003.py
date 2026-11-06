import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# try find to get everything
files = fs.find(base)
print("find count:", len(files))
names = sorted(f.split('/')[-1] for f in files)
print(names[:3], names[-3:])
