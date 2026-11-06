
nt=len(tgt)
tdoy=np.array([doy(d) for d in tgt])
Tt=T[tdoy-1]  # (nt,ny,nx)
S=sub[tidx]
with np.errstate(invalid='ignore'):
    hot=(S>=Tt)&finite_all[None]
mhw=np.zeros((nt,ny,nx),bool)
for iy in range(ny):
    for ix in range(nx):
        if not finite_all[iy,ix]: continue
        h=hot[:,iy,ix]
        # runs of hot
        runs=[]; t=0
        while t<nt:
            if h[t]:
                s=t
                while t<nt and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        # join runs with gap of 1-2 non-hot days
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1)<=2 and (r[0]-merged[-1][1]-1)>=1:
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,iy,ix]=True
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<nt:
    if active[t]:
        s=t
        while t<nt and active[t]: t+=1
        events.append({"onset":tgt[s].isoformat(),"end":tgt[t-1].isoformat()})
    else: t+=1
print(mhw.sum(), active.sum(), events)
