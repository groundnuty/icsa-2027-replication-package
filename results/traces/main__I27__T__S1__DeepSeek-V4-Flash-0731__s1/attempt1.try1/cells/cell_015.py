
import fsspec
fs = fsspec.filesystem('onedata')
# Let's use the underlying client to list all children
client = fs.client
# First, get the file ID for s1z
file_id = client.get_file_id('icsa2027_data_20261101T090944Z/s1z')
print("File ID:", file_id)
# Then list children
children = client.list_children(file_id)
print(type(children))
print(len(children) if hasattr(children, '__len__') else 'no len')
if hasattr(children, '__iter__'):
    items = list(children)
    print(len(items))
