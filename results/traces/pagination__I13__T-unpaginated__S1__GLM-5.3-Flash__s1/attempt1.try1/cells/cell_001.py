import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
try:
    lst = fs.ls(base, detail=True)
    print('OK relative, n =', len(lst))
    for it in lst[:80]:
        print(it.get('name'), '|', it.get('type'), '|', it.get('size'))
except Exception as e:
    print('ERR relative:', repr(e))
    try:
        lst = fs.ls('/' + base, detail=True)
        print('OK slash-prefixed, n =', len(lst))
        for it in lst[:80]:
            print(it.get('name'), '|', it.get('type'), '|', it.get('size'))
    except Exception as e2:
        print('ERR slash:', repr(e2))