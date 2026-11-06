import fsspec
fs = fsspec.filesystem('onedata')
root_path = 'icsa2027_data_20261101T090944Z'
all_files = fs.find(root_path)
# Look for any file containing 'sst' and '2008' or '1992'
interesting_files = [f for f in all_files if 'sst' in f.lower() and ('2008' in f or '1992' in f)]
print(f"Found {len(interesting_files)} interesting files.")
if interesting_files:
    print(interesting_files[:10])
