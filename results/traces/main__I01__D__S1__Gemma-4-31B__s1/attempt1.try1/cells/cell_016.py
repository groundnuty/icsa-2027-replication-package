import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
all_files = fs.find(root)
# Try to find files containing 'sst' in any folder
sst_files = [f for f in all_files if 'sst' in f.lower()]
print(f"Total sst files: {len(sst_files)}")
if sst_files:
    # Sort and print unique years found in filenames
    import re
    years = set()
    for f in sst_files:
        match = re.search(r'(\d{4})', f)
        if match:
            years.add(match.group(1))
    print(f"Years found: {sorted(list(years))}")
