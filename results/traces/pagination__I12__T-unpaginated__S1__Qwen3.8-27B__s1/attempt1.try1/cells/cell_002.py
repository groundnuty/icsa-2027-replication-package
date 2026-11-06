import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(root)
print('total files:', len(files))
names = sorted(f.split('/')[-1] for f in files)
print('first:', names[:3], 'last:', names[-3:])
# sizes of a couple
for f in [root+'/sst_19911227.nc', root+'/sst_20090601.nc', root+'/sst_20030105.nc']:
    info = fs.info(f)
    print(f.split('/')[-1], info.get('size'))