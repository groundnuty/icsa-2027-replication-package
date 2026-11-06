import numpy as np, pickle, datetime as dt, json
t = np.load('/tmp/tgt.npz'); tgt = t['arr']; tdates = [s for s in t['dates']]
thr_sm = np.load('/tmp/thr_sm.npy')
mask = np.load('/tmp/mhw_mask.npy')          # (92, 3600)
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

counts = mask[:, sea].sum(axis=1)
for i in range(92):
    bar = '#' * int(counts[i]/50)
    print(f'{tdates[i]} doy{doy_tgt[i]:3d} cells_in_MHW={counts[i]:5d} hot_cells={hot[i,sea].sum():5d} {bar}')