import fsspec, os
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work',exist_ok=True)
for d in ['20190601','19920101','20030105']:
    try:
        fs.get(f'{base}/sst_{d}.nc', f'/work/sst_{d}.nc'); print(d,'ok', os.path.getsize(f'/work/sst_{d}.nc'))
    except Exception as e: print(d,'err',repr(e)[:300])