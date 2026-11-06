import fsspec
fs = fsspec.filesystem('onedata')
base2 = "icsa2027_data_20261101T090944Z/s2z"
det2 = fs.ls(base2, detail=True)
print("count:", len(det2))
names2 = [f['name'].split('/')[-1] for f in det2]
print("first:", names2[:3])
print("last:", names2[-3:])
# check for subdirs
subdirs = [f['name'] for f in det2 if f['type'] != 'file']
print("subdirs:", subdirs[:10])