
code = r'''
import numpy as np, pandas as pd, json, os
z=np.load('/tmp/w/sub.npz'); S=z['S']; dates=pd.DatetimeIndex(z['dates']); latv=z['lat']; lonv=z['lon']
t=np.load('/tmp/w/thr.npz'); thr=t['thr']
def doy(tt):
    if tt.month==2 and tt.day==29: return 60
    nl=pd.Timestamp(year=2001,month=tt.month,day=tt.day).dayofyear
    return nl+1 if tt.month>=3 else nl
tm=(dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
T=dates[tm]; ST=S[tm].astype(np.float64)
print('target days', len(T), T[0].date(), T[-1].date(), len(T))
finite_all=np.isfinite(ST).all(axis=0)   # (ny,nx)
sea=finite_all
print('sea cells', sea.sum(), 'of', sea.size)
td=np.array([doy(x) for x in T])-1
TH=thr[td]  # (nt,ny,nx)
hot=(ST>=TH)&sea[None]
ny,nx=sea.shape
mhw=np.zeros(hot.shape,bool)
def runs(b):
    r=[]; i=0; n=len(b)
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append((i,j)); i=j+1
        else: i+=1
    return r
gap_hist={}
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        rr=[r for r in runs(hot[:,y,x]) if r[1]-r[0]+1>=5]
        if not rr: continue
        # join across gaps of 1 or 2 non-hot days
        merged=[list(rr[0])]
        for a,b in rr[1:]:
            g=a-merged[-1][1]-1
            if g<=2: merged[-1][1]=b; gap_hist[g]=gap_hist.get(g,0)+1
            else: merged.append([a,b])
        for a,b in merged: mhw[a:b+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append((T[i].strftime('%Y-%m-%d'),T[j].strftime('%Y-%m-%d'),int(j-i+1))); i=j+1
    else: i+=1
print('events',events)
print('gap hist',gap_hist, 'mhw cell-days', mhw.sum(), 'active days', active.sum())
os.makedirs('/tmp/w/out',exist_ok=True)
np.savez('/tmp/w/res.npz',mhw=mhw,T=T.values.astype('datetime64[D]'),lat=latv,lon=lonv)
# diagnostics: days hot count per cell
print('hot cell-days', hot.sum(), 'sea days', sea.sum()*len(T))
'''
open('/tmp/w/s2.py','w').write(code)
r=subprocess.run(['python','/tmp/w/s2.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-3000:])