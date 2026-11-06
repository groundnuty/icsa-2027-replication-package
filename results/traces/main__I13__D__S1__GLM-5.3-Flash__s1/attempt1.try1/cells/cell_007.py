import fsspec, json
fs = fsspec.filesystem('onedata')
client = getattr(fs, 'client', None)
print(type(client))
# try low-level list_children
res = client.list_children('icsa2027_data_20261101T090944Z/s1z', limit=1000)
print(type(res))
print([k for k in res.keys()])
print(len(res['children']))
print('token key candidates:', {k: res[k] for k in res if 'oken' in k or 'ontinuation' in k})
