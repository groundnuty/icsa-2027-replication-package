import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'
# Use find instead of ls if available, or just loop through subdirs
all_files = []
def walk(path):
    for item in fs.ls(path):
        if fs.isdir(item):
            walk(item)
        else:
            all_files.append(item)

# fs.isdir might not be available. Let's check.
try:
    walk(root)
except Exception as e:
    print(f"Walk failed: {e}")

print(f"Total files found: {len(all_files)}")
if all_files:
    print(f"First 5: {all_files[:5]}")
    print(f"Last 5: {all_files[-5:]}")
