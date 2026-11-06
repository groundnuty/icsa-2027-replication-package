
import fsspec
fs = fsspec.filesystem('onedata')
for p in ['/icsa2027_data_20261101T090944Z', '/']:
    try:
        entries = fs.ls(p, detail=True)
        print(p, "num:", len(entries))
        for e in entries[:50]:
            print(" ", e['name'], e['type'], e.get('size'))
    except Exception as ex:
        print(p, "ERR", ex)
