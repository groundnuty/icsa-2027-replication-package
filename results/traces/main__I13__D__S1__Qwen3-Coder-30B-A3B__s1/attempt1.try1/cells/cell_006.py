# Let me try to understand the dataset better by examining what's available
import fsspec
import os

fs = fsspec.filesystem('onedata')
# Let's see if we can access the root level
root_paths = fs.ls('/')
print("Root paths:")
for path in root_paths:
    print(f"  {path}")

# Look for any paths containing "cmems"
all_paths = []
def explore_paths(path, depth=0):
    if depth > 3: return
    try:
        items = fs.ls(path)
        for item in items:
            all_paths.append(item)
            if fs.isdir(item):
                explore_paths(item, depth+1)
    except:
        pass

explore_paths('/', 1)
print(f"\nFound {len(all_paths)} paths")

# Look for any path containing "cmems"
cmems_paths = [p for p in all_paths if 'cmems' in p.lower()]
print("Paths containing 'cmems':")
for p in cmems_paths[:10]:
    print(f"  {p}")