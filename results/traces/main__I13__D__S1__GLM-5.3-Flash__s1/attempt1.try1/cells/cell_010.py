import fsspec
fs = fsspec.filesystem('onedata')
client = fs.client
res = client.list_children('icsa2027_data_20261101T090944Z', file_path='s1z', limit=1000)
print(type(res), len(res['children']))
extra = {k: v for k, v in res.items() if k != 'children'}
print(extra)
