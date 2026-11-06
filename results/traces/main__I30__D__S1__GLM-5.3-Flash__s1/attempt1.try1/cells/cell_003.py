import fsspec
fs = fsspec.filesystem('onedata')
for path in ['icsa2027_data_20261101T090944Z', '/']:
    try:
        ls = fs.ls(path)
        print(path, '->', len(ls))
        for p in ls[:30]:
            print('   ', p)
    except Exception as e:
        print(path, 'ERROR', e)
