tidx=[i for i,d in enumerate(dates) if dt.date(2008,6,1)<=d<=dt.date(2008,8,31)]
tdates=[dates[i] for i in tidx]
T=V[tidx]  # (92,60,60)
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(), 'target days',len(tdates), tdates[0], tdates[-1])
doys=np.array([doy(d) for d in tdates])
th=thr_s[doys-1]  # (92,60,60)
with np.errstate(invalid='ignore'):
    hot=(T>=th)&sea[None]
mhw=np.zeros_like(hot)
def runs(b):
    out=[];n=len(b);i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
ncell=0
for y in range(60):
    for x in range(60):
        if not sea[y,x]: continue
        b=hot[:,y,x]
        segs=[s for s in runs(b) if s[1]-s[0]+1>=5]
        if not segs: continue
        # join segments with gaps of 1 or 2 non-hot days
        merged=[list(segs[0])]
        for s in segs[1:]:
            gap=s[0]-merged[-1][1]-1
            if gap<=2: merged[-1][1]=s[1]
            else: merged.append(list(s))
        for a,bb in merged:
            mhw[a:bb+1,y,x]=True; ncell+=1
print('cell MHW segments',ncell)
active=mhw.any(axis=(1,2))
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append((tdates[i].isoformat(),tdates[j].isoformat())); i=j+1
    else: i+=1
print(events)
print('hot days any',hot.any(axis=(1,2)).sum(), 'active days', active.sum())