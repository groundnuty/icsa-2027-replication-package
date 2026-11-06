
import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at how fs uses the path format
# The path format is /space_name/path
# Let me check with the leading slash
path = '/icsa2027_data_20261101T090944Z/s1z'
try:
    file_id = fs.client.get_file_id(path)
    print("File ID:", file_id)
    children = list(fs.client.list_children(file_id))
    print("Number of children:", len(children))
except Exception as e:
    print(f"Error: {e}")
