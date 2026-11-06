import fsspec
fs = fsspec.filesystem('onedata')
all_files = fs.find('icsa2027_data_20261101T090944Z')
files_2008 = [f for f in all_files if '2008' in f]
print(f"Total files with '2008': {len(files_2008)}")
if files_2008:
    print(files_2008[:10])
