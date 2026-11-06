
T=len(doy_tgt); nlat,nlon=A.shape[1:]
thr_t=thr_s[doy_tgt-1]  # (T,lat,lon)
hot=(Tt>=thr_t)
mhw=np.zeros((T,nlat,nlon),bool)
for i in range(nlat):
    for j in range(nlon):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs of hot
        runs=[]; k=0
        while k<T:
            if h[k]:
                s=k
                while k<T and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        # join gaps of 1-2 non-hot days
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1 in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0
while k<T:
    if active[k]:
        s=k
        while k<T and active[k]: k+=1
        events.append({"onset":str(tt_dates[s].date()),"end":str(tt_dates[k-1].date())})
    else: k+=1
print(events, mhw.sum(), active.sum())
