import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base)
print(len(files))
print(files[0])
print(files[-1])
# check if there are non .nc files
suffixes = set(f.split('.')[-1] for f in files)
print(suffixes)
names = sorted(f.rsplit('/',1)[-1] for f in files)
print(names[0], names[-1])
