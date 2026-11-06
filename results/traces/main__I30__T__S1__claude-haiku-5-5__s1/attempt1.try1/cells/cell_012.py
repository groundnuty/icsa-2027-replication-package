
tgt=[i for i,d in enumerate(dates) if d>=dt.date(2010,6,1) and d<=dt.date(2010,8,31)]
T=sst[tgt]; tdates=[dates[i] for i in tgt]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'target days',len(tdates), tdates[0],tdates[-1])
print('sea cells with NaN threshold:', (sea & np.isnan(thr_s).any(axis=0)).sum())
print('baseline dtype range', np.nanmin(sst), np.nanmax(sst))
doys=np.array([doy(d) for d in tdates])
H=T>=thr_s[doys-1]   # (days,ny,nx)
H&=sea[None]
mhw=np.zeros_like(H)
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        h=H[:,y,x].copy()
        # runs
        runs=[]; s=None
        for t in range(len(h)+1):
            v = h[t] if t<len(h) else False
            if v and s is None: s=t
            if (not v) and s is not None:
                if t-s>=5: runs.append([s,t-1])
                s=None
        # join gaps of 1-2 days
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1 in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        m=np.zeros(len(h),bool)
        for a,bb in merged: m[a:bb+1]=True
        mhw[:,y,x]=m
active=mhw.any(axis=(1,2))
print('active days',active.sum())
events=[]; s=None
for t in range(len(active)+1):
    v=active[t] if t<len(active) else False
    if v and s is None: s=t
    if (not v) and s is not None:
        events.append((tdates[s],tdates[t-1])); s=None
for e in events: print(e[0],e[1])
