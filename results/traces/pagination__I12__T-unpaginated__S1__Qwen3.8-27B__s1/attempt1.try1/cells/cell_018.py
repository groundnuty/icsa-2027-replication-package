import numpy as np, pickle, datetime as dt
t = np.load('/tmp/tgt.npz'); tgt = t['arr']; tdates = [s for s in t['dates']]
thr_sm = np.load('/tmp/thr_sm.npy')
mask = np.load('/tmp/mhw_mask.npy')
finite_tgt = np.all(np.isfinite(tgt), axis=0).reshape(3600)
sea = np.where(finite_tgt)[0]
doy_of_md = {}
d = dt.date(2000,1,1)
while d.year == 2000:
    doy_of_md[(d.month, d.day)] = d.timetuple().tm_yday
    d += dt.timedelta(days=1)
td = [dt.date.fromisoformat(s) for s in tdates]
doy_tgt = np.array([doy_of_md[(x.month, x.day)] for x in td])
tgt_flat = tgt.reshape(92, 3600)
hot = tgt_flat >= thr_sm[doy_tgt]

def show(c):
    print(f'--- cell {c} (flat) ---')
    for i in range(20, 42):
        flag = 'H' if hot[i,c] else ('*' if mask[i,c] else '.')
        print(f'{tdates[i]} SST={tgt_flat[i,c]:9.4f} thr={thr_sm[doy_tgt[i],c]:9.4f} {flag}')
# pick a cell whose MHW spans the whole event, and one with a gap inside
cnt = mask[:, sea].sum(axis=0)
c1 = int(sea[np.argmax(cnt)])
# find a cell with internal non-hot day inside MHW
gapcells = []
for c in sea:
    m = mask[:, c]
    if m.any():
        s = np.argmax(m); e = 91 - np.argmax(m[::-1])
        if not m[s:e+1].all():
            gapcells.append((c, e-s+1))
print('cells with internal gap:', len(gapcells))
show(c1)
if gapcells:
    show(gapcells[0][0])