import numpy as np, pickle
from datetime import date, timedelta
z = np.load('work/sst.npz')
ST = z['ST']; tt = z['tt']; SB = z['SB']
z2 = np.load('work/thr.npz')
thr, thr_s, clim_s, sea = z2['thr'], z2['thr_s'], z2['clim_s'], z2['sea']
n_cells = 3600
STf = ST.reshape(92, n_cells)
with open('work/pool_idx.pkl','rb') as fh: pool_idx = pickle.load(fh)
doy_md = {}
d = date(2004,1,1)
for k in range(366):
    doy_md[k+1] = (d.month, d.day); d += timedelta(days=1)
md2d = {v:k for k,v in doy_md.items()}
t_doys = np.array([md2d[(date.fromisoformat(ts.astype('datetime64[D]').astype(str)).month,
                         date.fromisoformat(ts.astype('datetime64[D]').astype(str)).day)] for ts in tt])

# region-mean 2004 SST vs climatology
reg = np.nanmean(STf[:, sea], axis=1)
cli = clim_s[:, t_doys-1][sea].mean(axis=1)
print("region-mean 2004 SST: min %.2f max %.2f" % (reg.min(), reg.max()))
print("region-mean clim (smoothed): min %.2f max %.2f" % (cli.min(), cli.max()))
print("mean offset 2004 - clim: %.3f K" % (reg - cli).mean())
print("daily offset (first/last):", np.round(reg[:3]-cli[:3],2), np.round(reg[-3:]-cli[-3:],2))

# margin analysis vs smoothed threshold
margin = STf - thr_s[:, t_doys-1].T
margin = np.where(sea[None,:], margin, np.nan)
maxm = np.nanmax(margin, axis=1)
print("daily max margin over sea cells (K): min %.3f, max %.3f" % (maxm.min(), maxm.max()))
top = np.argsort(maxm)[::-1][:10]
for i in top:
    c = int(np.nanargmax(margin[i]))
    print(tt[i].astype('datetime64[D]'), "max margin %.3f K at cell %d (lat %.2f lon %.2f) SST %.2f thr %.2f"
          % (maxm[i], c, z['lat'][c//60], z['lon'][c%60], STf[i,c], thr_s[c, t_doys[i]-1]))

# consecutive max-margin>=0 runs
runs = []
inrun = False
for i in range(92):
    if maxm[i] >= 0 and not inrun: s=i; inrun=True
    elif maxm[i] < 0 and inrun: runs.append((s, i-1)); inrun=False
if inrun: runs.append((s, 91))
print("runs with any hot cell:", [(str(tt[a].astype('datetime64[D]')), str(tt[b].astype('datetime64[D]')), b-a+1) for a,b in runs])
