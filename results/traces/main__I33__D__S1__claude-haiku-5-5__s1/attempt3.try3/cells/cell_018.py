code = r'''
import numpy as np, datetime, json, os
z=np.load('/work/region.npz')
dates=np.array([datetime.date.fromisoformat(s) for s in z['dates']]); sst=z['sst']; LAT=z['lat']; LON=z['lon']
def doy(d):
    return (datetime.date(2000,d.month,d.day)-datetime.date(2000,1,1)).days+1
assert doy(datetime.date(1992,2,28))==59 and doy(datetime.date(1993,3,1))==61 and doy(datetime.date(1993,12,31))==366
assert doy(datetime.date(1996,2,29))==60 and doy(datetime.date(1993,12,30))==365
bs=datetime.date(1992,1,1); be=datetime.date(2002,12,31)
idx_of={d:i for i,d in enumerate(dates)}
pools={k:set() for k in range(1,367) if k!=60}
for b in dates:
    if not (bs<=b<=be): continue
    k=doy(b)
    if k==60: continue
    for off in range(-5,6):
        pools[k].add(b+datetime.timedelta(off))
print('pool sizes', [len(pools[k]) for k in (1,59,61,366,365)])
print('pool missing', sum(1 for k in pools for d in pools[k] if d not in idx_of))
ncell=sst.shape[1:]
thr=np.full((367,)+ncell,np.nan); clim=np.full((367,)+ncell,np.nan)
for k in range(1,367):
    if k==60: continue
    ii=sorted(idx_of[d] for d in pools[k] if d in idx_of)
    vals=sst[ii]
    thr[k]=np.nanquantile(vals,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(vals,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    # a: (367,...) index 0 unused; days 1..366 circular 31-day mean
    b=a[1:]  # 366
    out=np.empty_like(b)
    for d in range(366):
        ids=[(d+o)%366 for o in range(-15,16)]
        out[d]=b[ids].mean(axis=0)
    r=np.full_like(a,np.nan); r[1:]=out; return r
thr_s=smooth(thr); clim_s=smooth(clim)
# sea cells
tm=np.array([datetime.date.fromisoformat(s) for s in ['2014-06-01']])
tstart=datetime.date(2014,6,1); tend=datetime.date(2014,8,31)
tidx=[i for i,d in enumerate(dates) if tstart<=d<=tend]
tdates=[dates[i] for i in tidx]
T=sst[tidx]  # (92,lat,lon)
sea=np.all(np.isfinite(T),axis=0)
print('target days', len(tdates), tdates[0], tdates[-1], 'sea cells', sea.sum(), 'of', sea.size)
print('thr nan in sea cells (summer)', np.isnan(thr_s[[doy(d) for d in tdates]][:,sea]).sum())
hot=np.zeros(T.shape,bool)
dk=np.array([doy(d) for d in tdates])
for j in range(len(tdates)):
    hot[j]=(T[j]>=thr_s[dk[j]])
hot&=sea[None]
mhw=np.zeros(T.shape,bool)
nt,nl,nn=T.shape
for la in range(nl):
    for lo in range(nn):
        if not sea[la,lo]: continue
        h=hot[:,la,lo]
        # runs
        runs=[]; j=0
        while j<nt:
            if h[j]:
                s=j
                while j<nt and h[j]: j+=1
                if j-s>=5: runs.append([s,j-1])
            else: j+=1
        # join gaps of 1-2 non-hot days
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1) in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,la,lo]=True
active=mhw.any(axis=(1,2))
events=[]; j=0
while j<nt:
    if active[j]:
        s=j
        while j<nt and active[j]: j+=1
        events.append((tdates[s],tdates[j-1]))
    else: j+=1
print('events', [(str(a),str(b)) for a,b in events])
print('mhw cell-days', mhw.sum(), 'active days', active.sum(), 'hot cell-days', hot.sum())
os.makedirs('/work/output',exist_ok=True)
np.savez('/work/res.npz', mhw=mhw, sea=sea, tdates=np.array([str(d) for d in tdates]), LAT=LAT, LON=LON)
json.dump({'events':[(str(a),str(b)) for a,b in events]}, open('/work/events.json','w'))
print('baseline ndays', sum(1 for d in dates if bs<=d<=be), 'first', dates[0])
'''
open('/work/run.py','w').write(code)
import subprocess
r=subprocess.run(['python','/work/run.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-3000:])