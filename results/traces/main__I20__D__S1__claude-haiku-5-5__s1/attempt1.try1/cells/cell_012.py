doys=np.array([doy(d) for d in tgt])
H=np.zeros((92,)+sea.shape,bool)
for t in range(92):
    H[t]=(T[t]>=thrS[doys[t]-1])&sea
def runs(b):
    # returns list of (s,e) inclusive runs of True
    r=[];i=0;n=len(b)
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append((i,j)); i=j+1
        else: i+=1
    return r
M=np.zeros_like(H)
ny,nx=sea.shape
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        h=H[:,y,x]
        rs=[r for r in runs(h) if r[1]-r[0]+1>=5]
        if not rs: continue
        # merge with gaps of 1-2 non-hot days
        merged=[list(rs[0])]
        for s,e in rs[1:]:
            gap=s-merged[-1][1]-1
            if gap<=2: merged[-1][1]=e
            else: merged.append([s,e])
        for s,e in merged: M[s:e+1,y,x]=True
active=M.any(axis=(1,2))
ev=[]
for s,e in runs(active):
    ev.append({"onset":str(tgt[s]),"end":str(tgt[e])})
print('per-cell MHW cell-days', M.sum(), 'active days', active.sum())
print(ev)