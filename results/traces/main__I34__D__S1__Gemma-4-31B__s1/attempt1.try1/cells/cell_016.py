import fsspec
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z'

# Manually walk and search for '2007'
def search_for_year(path, year):
    try:
        items = fs.ls(path)
        for item in items:
            if fs.isdir(item):
                search_for_year(item, year)
            elif year in item:
                print(f"Found: {item}")
    except Exception as e:
        pass

search_for_year(root, '2007')
