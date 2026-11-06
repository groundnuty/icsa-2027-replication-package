import fsspec
fs = fsspec.filesystem('onedata')
# List all directories in the root
all_files = fs.find('')
dirs = set([os.path.dirname(f) for f in all_files])
print(f"All directories: {sorted(list(dirs))}")
