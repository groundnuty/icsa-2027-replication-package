import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'

def find_dataset(path, target):
    try:
        for entry in fs.ls(path):
            if target in entry:
                print(f"Found: {entry}")
            # This doesn't handle nested directories recursively if fs.ls is not recursive
            # Let's check if it's a directory
            # Unfortunately, fsspec.ls might not distinguish directories easily without more checks
            pass
    except Exception:
        pass

# Better way: recursive search if possible or list all
# Try to list the entire tree
def walk(path):
    try:
        for entry in fs.ls(path):
            # Checking if it's likely a directory (this is heuristic)
            # On some filesystems, directories don't have extensions or are listed as such
            # Let's just try to ls it.
            try:
                fs.ls(entry)
                # It's a directory
                walk(entry)
            except:
                # It's a file
                if 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m' in entry:
                    print(f"Found: {entry}")
    except Exception:
        pass

walk(root)
