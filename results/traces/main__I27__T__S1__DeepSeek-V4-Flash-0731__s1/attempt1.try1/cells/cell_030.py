
import fsspec
fs = fsspec.filesystem('onedata')
# Try to use list_children directly with pagination
client = fs.client
space = 'icsa2027_data_20261101T090944Z'
# Try calling list_children with different parameters
import inspect
src = inspect.getsource(type(client).list_children)
print(src)
