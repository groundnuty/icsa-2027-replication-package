import fsspec
import os

fs = fsspec.filesystem('onedata')
root_path = 'icsa2027_data_20261101T090944Z'
all_files = fs.find(root_path)

# Search for files from 2008 and 1992-2002
target_files = [f for f in all_files if 'sst' in f.lower() and '2008' in f]
baseline_files = [f for f in all_files if 'sst' in f.lower() and any(year in f for year in [str(y) for y in range(1992, 2003)])]

print(f"Target files found: {len(target_files)}")
print(f"Baseline files found: {len(baseline_files)}")

if target_files:
    print(f"Sample target file: {target_files[0]}")
if baseline_files:
    print(f"Sample baseline file: {baseline_files[0]}")
