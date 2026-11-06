import fsspec, re
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
allnames = []
marker = None
# try listing with pagination
try:
    while True:
        entries = fs.ls(base, detail=False) if marker is None else fs.ls(base, detail=False, marker=marker)
        allnames += entries
        if len(entries) < 1000:
            break
        marker = entries[-1]
except TypeError:
    entries = fs.ls(base, detail=False)
    allnames = entries
    print('no pagination support; got', len(entries))

print('total names:', len(allnames))
dates = sorted(re.findall(r'sst_(\d{8})\.nc', ' '.join(allnames)))
print('first:', dates[0], 'last:', dates[-1])
# check gaps
ds = set(dates)
print('count dates:', len(dates), 'unique:', len(ds))
