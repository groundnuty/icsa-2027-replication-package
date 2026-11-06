
D=DOY[tgt_idx]
hot=np.zeros((len(tgt_idx),60,60),bool)
for j in range(len(tgt_idx)):
    hot[j]=(tgt[j]>=thrS[D[j]])
hot &= sea[None]
mhw=np.zeros_like(hot)
nT=len(tgt_idx)
for a in range(60):
    for b in range(60):
        if not sea[a,b]: continue
        h=hot[:,a,b]
        # maximal hot runs
        segs=[]; j=0
        while j<nT:
            if h[j]:
                k=j
                while k<nT and h[k]: k+=1
                if k-j>=5: segs.append([j,k-1])
                j=k
            else: j+=1
        # join segments separated by 1 or 2 non-hot days
        merged=[]
        for s in segs:
            if merged and (s[0]-merged[-1][1]-1) in (1,2):
                merged[-1][1]=s[1]
            else: merged.append(list(s))
        for s,e in merged: mhw[s:e+1,a,b]=True
active=mhw.any(axis=(1,2))
# events
events=[]; j=0
while j<nT:
    if active[j]:
        k=j
        while k<nT and active[k]: k+=1
        events.append((T[tgt_idx[j]],T[tgt_idx[k-1]])); j=k
    else: j+=1
print(len(events))
for e in events: print(e[0].date(), e[1].date())
print('mhw cell-days', mhw.sum(), 'active days', active.sum())
