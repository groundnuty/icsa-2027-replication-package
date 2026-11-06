
import fsspec
fs = fsspec.filesystem('onedata')
# Try to get more info about the listing
# Maybe use a different listing approach
import onedatarestfsspec
print(dir(onedatarestfsspec))

# Let me check the client
client = fs.client
print(type(client))
print([m for m in dir(client) if not m.startswith('_')][:50])
