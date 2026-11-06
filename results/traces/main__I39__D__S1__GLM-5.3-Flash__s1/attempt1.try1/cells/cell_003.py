import fsspec
fs = fsspec.filesystem('onedata')
# check parent dir
try:
    entries = fs.ls('icsa2027_data_20261101T090944Z', detail=True)
    print('parent entries:')
    for e in entries:
        print(e.get('type'), e.get('name'))
except Exception as ex:
    print('ERR parent', type(ex).__name__, ex)

# check space root
try:
    entries = fs.ls('/', detail=True)
    print('space root entries:')
    for e in entries[:50]:
        print(e.get('type'), e.get('name'))
except Exception as ex:
    print('ERR root', type(ex).__name__, ex)
