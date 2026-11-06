import fsspec
fs = fsspec.filesystem('onedata')
for p in ['/icsa2027_data_20261101T090944Z/s1z', 'icsa2027_data_20261101T090944Z/s1z']:
    try:
        entries = fs.ls(p)
        print(repr(p), 'OK, n=', len(entries))
        for e in entries[:40]:
            print('  ', e)
        break
    except Exception as ex:
        print(repr(p), 'ERR', repr(ex)[:300])
