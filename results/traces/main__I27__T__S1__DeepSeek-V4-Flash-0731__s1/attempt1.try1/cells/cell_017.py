
import fsspec
fs = fsspec.filesystem('onedata')
# Let's look at how fs internally resolves paths
# Check fs info for a file
info = fs.info('icsa2027_data_20261101T090944Z/s1z/sst_19920101.nc')
print(info)

# Let's see the space name
# fs.ls used "icsa2027_data_20261101T090944Z/s1z" as relative path
# But the client expects space name first
# Let's check what spaces exist
spaces = fs.client.list_spaces()
print("Spaces:", spaces)
