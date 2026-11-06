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
mask = np.isfinite(excess)
vals = excess[mask]
print('finite excess count:', vals.size, 'of', excess.size)
print('percentiles of excess:', [round(float(np.percentile(vals, p)),3) for p in [0,1,5,10,25,50,75,90,95,99,100]])
print('max finite excess:', float(vals.max()))
# top 5 finite near-ties
idx = np.dstack(np.unravel_index(np.argsort(np.where(mask, excess, -np.inf), axis=None)[-5:], excess.shape))[0]
for kk, rr, cc in idx[::-1]:
    print(tg[kk], (rr,cc), 'SST', repr(float(tg_data[kk,rr,cc])), 'thr', repr(float(thr_s[tg_doy[kk]-1, rr, cc])), 'diff', float(excess[kk,rr,cc]))
# top cells by max excess
mx = np.where(mask, excess, -np.inf).max(axis=0)
print('cells with max excess > -0.05:', int((mx > -0.05).sum()), ' > -0.1:', int((mx > -0.1).sum()), ' > -0.25:', int((mx > -0.25).sum()))
