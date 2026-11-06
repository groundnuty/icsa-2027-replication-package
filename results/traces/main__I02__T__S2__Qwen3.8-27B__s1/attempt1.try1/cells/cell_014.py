import numpy as np, pickle
from datetime import date, timedelta
z = np.load('work/sst.npz')
ST = z['ST']; tt = z['tt']; SB = z['SB']
z2 = np.load('work/thr.npz')
thr, thr_s, sea = z2['thr'], z2['thr_s'], z2['sea']
n_cells = 3600
STf = ST.reshape(92, n_cells)
SBf = SB.reshape(4028, n_cells)
with open('work/pool_idx.pkl','rb') as fh: pool_idx = pickle.load(fh)

doy_md = {}
d = date(2004,1,1)
for k in range(366):
    doy_md[k+1] = (d.month, d.day); d += timedelta(days=1)
md2d = {v:k for k,v in doy_md.items()}
t_doys = np.array([md2d[(lambda x: (x.month, x.day))(date.fromisoformat(ts.astype('datetime64[D]').astype(str)))] for ts in tt])

raw_hot = (STf >= thr[:, t_doys-1].T)
smo_hot = (STf >= thr_s[:, t_doys-1].T)
print("raw hot frac (sea):", float(raw_hot[:, sea].mean()))
print("smoothed hot frac (sea):", float(smo_hot[:, sea].mean()))

# per-doy raw hot fraction
for i, dd in enumerate(t_doys[::10]):
    print("doy", dd, "raw %.3f" % raw_hot[i, sea].mean(), "smooth %.3f" % smo_hot[i, sea].mean())

# compare 2004 summer SST dist vs baseline pool dist for central sea cells
c = 1799
pool = SBf[pool_idx[197], c]; pool = pool[np.isfinite(pool)]
# 2004 values on the same calendar window dates (Jul 12 - Jul 22, 2004):
win_dates = [date(2004,7,12)+timedelta(k) for k in range(11)]
i0 = np.searchsorted(z['tb'], np.datetime64('1991-12-27'))
tidx = np.searchsorted(z['tt'], np.datetime64('2004-07-12'))
vals2004 = STf[tidx:tidx+11, c]
print("2004 window SSTs:", np.round(vals2004, 2))
print("2004 window: min %.2f max %.2f mean %.2f p90 %.2f" % (vals2004.min(), vals2004.max(), vals2004.mean(), np.quantile(vals2004, 0.9, method='hazen')))
print("baseline pool: min %.2f max %.2f mean %.2f p90 %.2f" % (pool.min(), pool.max(), pool.mean(), np.quantile(pool, 0.9, method='hazen')))
# how many baseline pool values are below the smoothed thr for 197?
print("P(pool < thr_s197):", float((pool < thr_s[c,196]).mean()))
