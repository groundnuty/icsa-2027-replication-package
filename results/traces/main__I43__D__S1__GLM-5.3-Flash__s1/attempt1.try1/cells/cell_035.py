import numpy as np, json, datetime as dt
data = np.load('/work/data.npy')
thr_s = np.load('/work/thr_s.npy').reshape(366,60,60)
meta = json.load(open('/work/dates.json'))
tg = [dt.date.fromisoformat(s) for s in meta['target']]
tg_data = data[4028:4120]
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(d): return cum[d.month-1] + d.day
tg_doy = np.array([md_doy(d) for d in tg])
excess = tg_data - thr_s[tg_doy-1]
k, r, c = np.unravel_index(np.nanargmax(excess), excess.shape)
print('closest approach:', tg[k], 'cell', (r,c), 'SST', repr(float(tg_data[k,r,c])), 'thr', repr(float(thr_s[tg_doy[k]-1, r, c])), 'diff', float(excess[k,r,c]))
# top 10 near-ties
idx = np.dstack(np.unravel_index(np.argsort(excess, axis=None)[-10:], excess.shape))[0]
for kk, rr, cc in idx[::-1]:
    print(tg[kk], (rr,cc), 'SST', round(float(tg_data[kk,rr,cc]),4), 'thr', round(float(thr_s[tg_doy[kk]-1, rr, cc]),4), 'diff', round(float(excess[kk,rr,cc]),4))
