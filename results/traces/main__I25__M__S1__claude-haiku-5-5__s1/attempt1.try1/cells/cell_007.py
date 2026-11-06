doys=np.array([doy(x) for x in tgt])
Tt=Ts[doys-1]  # (92,ny,nx)
hot=(S>=Tt)&sea[None]
mhw=np.zeros_like(hot)
ncell=0
for j in range(ny):
    for i in range(nx):
        if not sea[j,i]: continue
        h=hot[:,j,i]
        # runs
        runs=[]; t=0; n=len(h)
        while t<n:
            if h[t]:
                s0=t
                while t<n and h[t]: t+=1
                if t-s0>=5: runs.append([s0,t-1])
            else: t+=1
        # join gaps 1-2
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1 in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for a,b in merged:
            mhw[a:b+1,j,i]=True
        ncell+=len(merged)>0
print('cells with MHW',ncell)
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<len(active):
    if active[t]:
        s0=t
        while t<len(active) and active[t]: t+=1
        events.append((tgt[s0].isoformat(), tgt[t-1].isoformat()))
    else: t+=1
print(events)
print(mhw.sum(), active.sum())