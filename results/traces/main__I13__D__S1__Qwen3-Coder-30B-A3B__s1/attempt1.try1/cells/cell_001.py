import fsspec
fs = fsspec.filesystem('onedata')
contents = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
print("Directory contents:")
for item in contents:
    print(f"  {item}")