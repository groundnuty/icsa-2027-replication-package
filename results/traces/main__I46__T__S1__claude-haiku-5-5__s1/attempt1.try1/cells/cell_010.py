
tgt=[d for d in dates if dt.date(2013,6,1)<=d<=dt.date(2013,8,31)]
ti=[idx[d] for d in tgt]
T=S[ti]  # (92,60,60)
sea=np.all(np.isfinite(T),axis=0)
print('tgt days',len(tgt), 'sea cells', sea.sum(), 'partial-nan cells', (np.isfinite(T).any(0)&~sea).sum())
doys=np.array([doy(d) for d in tgt])
TH=thrS[doys]  # (92,60,60)
hot=(T>=TH)&sea[None]
ndays=len(tgt)
mask=np.zeros((ndays,60,60),bool)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # hot runs
        runs=[]; k=0
        while k<ndays:
            if h[k]:
                s=k
                while k<ndays and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        # join gaps of 1-2 days
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1) in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mask[s:e+1,i,j]=True
active=mask.any(axis=(1,2))
events=[]; k=0
while k<ndays:
    if active[k]:
        s=k
        while k<ndays and active[k]: k+=1
        events.append((tgt[s].isoformat(), tgt[k-1].isoformat()))
    else: k+=1
print(events)
print('active days', active.sum(), 'mask cells-days', mask.sum(), 'hot cell-days', hot.sum())
