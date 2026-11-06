import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
entries = fs.ls(root)
print(f"Entries in root: {entries}")

for entry in entries:
    try:
        sub_entries = fs.ls(entry)
        print(f"Entries in {entry}: {len(sub_entries)} files/dirs")
        # Sample some files from each entry
        for se in sub_entries[:5]:
            print(f"  {se}")
    except Exception as e:
        print(f"Error listing {entry}: {e}")
