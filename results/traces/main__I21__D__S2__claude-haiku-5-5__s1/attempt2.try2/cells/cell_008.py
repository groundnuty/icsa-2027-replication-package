
exec(open('/work/common.py').read())
nT=len(Tt)
thr_t = thr[Dt-1]           # (nT,60,60)
clim_t = clim[Dt-1]
hot = (At>=thr_t) & sea[None]
mhw = np.zeros((nT,60,60),dtype=np.uint8)
ncell_ev=0
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h = hot[:,i,j]
        # runs
        runs=[]; k=0
        while k<nT:
            if h[k]:
                s=k
                while k<nT and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        # join gaps of 1 or 2 non-hot days
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1) in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(r[:])
        for s,e in merged:
            mhw[s:e+1,i,j]=1
        ncell_ev+=len(merged)
print('per-cell events total', ncell_ev, 'mhw cell-days', mhw.sum())
active = mhw.reshape(nT,-1).any(axis=1)
events=[]; k=0
while k<nT:
    if active[k]:
        s=k
        while k<nT and active[k]: k+=1
        events.append((str(Tt[s].date()), str(Tt[k-1].date())))
    else: k+=1
print(events)
print('hot cell-days', hot.sum(), 'active days', active.sum())
