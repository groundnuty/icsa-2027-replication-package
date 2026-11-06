
import fsspec
fs = fsspec.filesystem('onedata')

# List all files to understand the time range
files = fs.ls('icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")
# Get first and last
print(f"First: {files[0]}")
print(f"Last: {files[-1]}")

# Check if we have baseline years (1992-2002) and target (2015)
baseline_files = [f for f in files if any(f'y{y}' in f for y in range(1992, 2003))]
target_files = [f for f in files if 'y2015' in f]
print(f"Baseline files (1992-2002): {len(baseline_files)}")
print(f"Target files (2015): {len(target_files)}")
