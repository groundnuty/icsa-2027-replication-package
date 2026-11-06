
tgt=[i for i,t in enumerate(days) if dt.date(2004,6,1)<=t<=dt.date(2004,8,31)]
T=A[tgt]; tdays=[days[i] for i in tgt]; nT=len(tgt)
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'ntarget',nT)
doys=np.array([doy2(t) for t in tdays])
TH=thrS[doys]  # nT,60,60
with np.errstate(invalid='ignore'):
    hot=(T>=TH)&np.isfinite(TH)&sea[None]
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
mhw=np.zeros((nT,60,60),bool)
for y in range(60):
    for x in range(60):
        if not sea[y,x]: continue
        r=[(a,b) for a,b in runs(hot[:,y,x]) if b-a+1>=5]
        if not r: continue
        # join events separated by 1 or 2 non-hot days
        groups=[list(r[0])]
        for a,b in r[1:]:
            if a-groups[-1][1]-1<=2: groups[-1][1]=b
            else: groups.append([a,b])
        for a,b in groups: mhw[a:b+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[]; i=0
while i<nT:
    if active[i]:
        j=i
        while j+1<nT and active[j+1]: j+=1
        events.append((tdays[i].isoformat(),tdays[j].isoformat())); i=j+1
    else: i+=1
print(events)
print('active days',active.sum(), 'mhw cell-days',mhw.sum())