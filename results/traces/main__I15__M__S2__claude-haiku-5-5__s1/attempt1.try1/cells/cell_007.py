
nt=len(ttime)
Tt=T[tdoy-1]  # (nt,ny,nx)
hot=(tv>=Tt)&sea[None]
mhw=np.zeros((nt,ny,nx),bool)
def runs(b):
    # returns list of (start,end) inclusive of maximal True runs
    r=[];i=0;n=len(b)
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            r.append((i,j)); i=j+1
        else: i+=1
    return r
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        rr=[r for r in runs(hot[:,y,x]) if r[1]-r[0]+1>=5]
        if not rr: continue
        # join if gap of 1 or 2 non-hot days
        groups=[list(rr[0])]
        for s,e in rr[1:]:
            gap=s-groups[-1][1]-1
            if gap<=2: groups[-1][1]=e
            else: groups.append([s,e])
        for s,e in groups: mhw[s:e+1,y,x]=True
active=mhw.any(axis=(1,2))
ev=[];i=0
while i<nt:
    if active[i]:
        j=i
        while j+1<nt and active[j+1]: j+=1
        ev.append({"onset":str(ttime[i].date()),"end":str(ttime[j].date())}); i=j+1
    else: i+=1
print(hot.sum(), mhw.sum(), active.sum()); print(ev)
