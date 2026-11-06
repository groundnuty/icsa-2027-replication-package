import fsspec
fs = fsspec.filesystem('onedata')
root_s2z = 'icsa2027_data_20261101T090944Z/s2z'
files_s2z = fs.ls(root_s2z)
print(f"Total files in s2z: {len(files_s2z)}")
print(f"First file in s2z: {files_s2z[0]}")
print(f"Last file in s2z: {files_s2z[-1]}")
