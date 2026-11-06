
code = r'''
import numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
z=np.load('/tmp/w/sub.npz'); S=z['S']; dates=pd.DatetimeIndex(z['dates']); latv=z['lat']; lonv=z['lon']
B0=pd.Timestamp('1991-12-27'); B1=pd.Timestamp('2003-01-05')
Ax=pd.date_range(B0,B1)
Sb=S[:len(Ax)].astype(np.float64)
assert (dates[:len(Ax)]==Ax).all()
def doy(t):
    if t.month==2 and t.day==29: return 60
    nl=pd.Timestamp(year=2001,month=t.month,day=t.day).dayofyear
    return nl+1 if t.month>=3 else nl
bmask=(Ax>=pd.Timestamp('1992-01-01'))&(Ax<=pd.Timestamp('2002-12-31'))
base_dates=Ax[bmask]
bdoy=np.array([doy(t) for t in base_dates])
pool_idx={}
for dd in range(1,367):
    if dd==60: continue
    bs=base_dates[bdoy==dd]
    sel=set()
    for b in bs:
        for k in range(-5,6): sel.add(b+pd.Timedelta(days=k))
    pool_idx[dd]=np.array([Ax.get_loc(t) for t in sorted(sel) if t in Ax])
ny,nx=S.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for dd,idx in pool_idx.items():
    P=Sb[idx]
    thr[dd]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(P,axis=0)
thr=thr[1:367]; clim=clim[1:367]
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[ids],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
np.savez('/tmp/w/thr.npz',thr=thr_s,clim=clim_s)
print('nan thr frac', np.isnan(thr_s).mean(), 'sample', thr_s[150,30,30], clim_s[150,30,30])
print('pool sizes', len(pool_idx[1]), 'base doy1 count', (bdoy==1).sum())
'''
open('/tmp/w/s1.py','w').write(code)
import subprocess
r=subprocess.run(['python','/tmp/w/s1.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-3000:])