import fsspec
fs = fsspec.filesystem('onedata')
print(f"s1z: {len(fs.ls('icsa2027_data_20261101T090944Z/s1z'))}")
print(f"s2z: {fs.ls('icsa2027_data_20261101T090944Z/s2z')}")
