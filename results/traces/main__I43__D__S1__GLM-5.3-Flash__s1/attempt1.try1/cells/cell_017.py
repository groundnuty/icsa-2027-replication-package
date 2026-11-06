import os, fsspec, time, datetime as dt, json
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
dates = json.load(open('/work/dates.json'))
need = [dt.date.fromisoformat(s) for s in dates['baseline_window'] + dates['target']]
have = set(f[4:12] for f in os.listdir('/work/nc') if f.endswith('.nc'))
remaining = [d for d in need if f'{d:%Y%m%d}' not in have]

B = 200
t_start = time.time()
for i in range(0, len(remaining), B):
    chunk = remaining[i:i+B]
    names = [p + f'/sst_{d:%Y%m%d}.nc' for d in chunk]
    fs.get(names, '/work/nc/')
    if (i//B) % 5 == 4:
        el = time.time()-t_start
        print(f'{i+B}/{len(remaining)} in {el:.0f}s', flush=True)
el = time.time()-t_start
print('DONE', len(remaining), 'files in', round(el,1), 's')
have = set(f[4:12] for f in os.listdir('/work/nc') if f.endswith('.nc'))
print('total files now:', len(have))
