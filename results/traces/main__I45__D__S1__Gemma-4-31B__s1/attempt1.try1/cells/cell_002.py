import fsspec

fs = fsspec.filesystem('onedata')
remote_dir = 'icsa2027_data_20261101T090944Z/s1z'
# List everything in the directory to see the structure
try:
    all_contents = fs.ls(remote_dir, detail=False)
    print(f"Total items in {remote_dir}: {len(all_contents)}")
    for item in sorted(all_contents)[:50]:
        print(item)
    if len(all_contents) > 50:
        print("...")
except Exception as e:
    print(f"Error: {e}")
