import onedatarestfsspec.core as core, inspect
from onedatarestfsspec.core import OnedataFileRESTClient
fs = fsspec_files = None
import fsspec
fs = fsspec.filesystem('onedata')
client = fs.client
space = 'icsa2027_data_20261101T090944Z'
res = client.list_children(space, file_path='s1z', attributes=["name","type","size"], limit=1000)
print("keys:", res.keys())
print("n children:", len(res["children"]))
for k,v in res.items():
    if k != 'children':
        print(k, "=>", str(v)[:200])
