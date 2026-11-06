
import fsspec
fs = fsspec.filesystem('onedata')
# Get file ID using the space
space = 'icsa2027_data_20261101T090944Z'
client = fs.client
# Try to resolve the path
path = f'{space}/s1z'
file_id = client.get_file_id(path)
print("File ID:", file_id)
# Now list children
children = list(client.list_children(file_id))
print("Number of children:", len(children))
if len(children) > 1000:
    print("First:", children[:3])
    print("Last:", children[-3:])
