import os, shutil, datetime as dt, json

# consolidate: move dl (1992-01-01..1992-07-18) and dl2 (1992-07-19..1993-02-03) into /work/nc
os.makedirs('/work/nc', exist_ok=True)
moved = 0
for src in ['/work/dl','/work/dl2']:
    for f in os.listdir(src):
        if f.endswith('.nc'):
            shutil.move(os.path.join(src,f), os.path.join('/work/nc',f))
            moved += 1
print('moved', moved)

dates = json.load(open('/work/dates.json'))
need = [dt.date.fromisoformat(s) for s in dates['baseline_window'] + dates['target']]
have = set(f[4:12] for f in os.listdir('/work/nc') if f.endswith('.nc'))
remaining = [d for d in need if f'{d:%Y%m%d}' not in have]
print('have', len(have), 'remaining', len(remaining))
print('first remaining', remaining[0], 'last', remaining[-1])
