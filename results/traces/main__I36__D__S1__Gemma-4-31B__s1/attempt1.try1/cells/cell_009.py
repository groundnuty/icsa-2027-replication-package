import fsspec
fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
# List all contents, not just files
contents = fs.ls(base_path, detail=False)
# If it's a large list, maybe it's paginated or something? 
# No, fsspec usually returns all.
print(f"Total items in s1z: {len(contents)}")
# Check if any are directories
# Usually fs.ls returns paths. Let's check if any path contains a '/' after the base_path.
# Wait, s1z is the directory.
dirs = [c for c in contents if fs.isdir(c)]
print(f"Directories in s1z: {dirs}")
