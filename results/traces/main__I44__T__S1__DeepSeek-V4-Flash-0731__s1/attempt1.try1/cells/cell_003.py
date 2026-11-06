import fsspec
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(len(files))
# Get the file names
names = [f.split('/')[-1] for f in files]
names.sort()
print(names[:5], names[-5:])
print(len(names))
