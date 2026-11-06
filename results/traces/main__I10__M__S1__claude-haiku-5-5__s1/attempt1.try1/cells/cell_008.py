tstart=dt.date(2005,6,1); tend=dt.date(2005,8,31)
tdates=[]; d=tstart
while d<=tend: tdates.append(d); d+=dt.timedelta(1)
ti=[idx[d] for d in tdates]
T=S[ti]  # days x ny x nx
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'target days',len(tdates))
tdoy=np.array([doy(d) for d in tdates])
thr_t=thr_s[tdoy]  # days x ny x nx
hot=(T>=thr_t)&sea[None]
print('thr nan on sea cells:', np.isnan(thr_s[1:][:, sea]).sum())
def runs(b):
    # return list of (start,end) inclusive of True runs
    out=[]; n=len(b); i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
mhw=np.zeros_like(hot)
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        h=hot[:,y,x]
        ev=[r for r in runs(h) if r[1]-r[0]+1>=5]
        # join gaps of 1 or 2 non-hot days
        merged=[]
        for r in ev:
            if merged and r[0]-merged[-1][1]-1<=2:
                merged[-1]=(merged[-1][0],r[1])
            else: merged.append(r)
        for a,b_ in merged: mhw[a:b_+1,y,x]=True
active=mhw.any(axis=(1,2))
print('active days',active.sum())
ev=runs(active)
events=[{"onset":tdates[a].isoformat(),"end":tdates[b_].isoformat()} for a,b_ in ev]
print(events)