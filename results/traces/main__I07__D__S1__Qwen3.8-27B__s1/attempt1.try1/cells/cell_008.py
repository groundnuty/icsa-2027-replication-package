import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for pat in [f'{base}/sst_1992*.nc', f'{base}/*.nc', f'{base}/sst_20210601.nc']:
    try:
        r = fs.glob(pat)
        print(pat, "->", len(r), r[:3])
    except Exception as e:
        print(pat, "ERR", type(e).__name__, str(e)[:200])
try:
    r = fs.find(base)
    print("find:", len(r))
except Exception as e:
    print("find ERR", type(e).__name__, str(e)[:200])
