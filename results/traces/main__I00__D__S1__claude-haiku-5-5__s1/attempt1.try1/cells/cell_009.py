T=len(tgt_idx)
ys,xs=np.where(sea)
mhw=np.zeros((T,)+ny,np.uint8)
hot=np.zeros((T,len(ys)),bool)
hotv=tgt[:,ys,xs]>=thr_s[tgt_doy][:,ys,xs]
for c in range(len(ys)):
    h=hotv[:,c]
    # runs of hot days
    runs=[];t=0
    while t<T:
        if h[t]:
            s=t
            while t<T and h[t]: t+=1
            if t-s>=5: runs.append([s,t-1])
        else: t+=1
    # join runs separated by 1-2 non-hot days
    merged=[]
    for r in runs:
        if merged and r[0]-merged[-1][1]-1<=2:
            merged[-1][1]=r[1]
        else: merged.append(r)
    for s,e in merged:
        mhw[s:e+1,ys[c],xs[c]]=1
active=mhw.reshape(T,-1).any(axis=1)
events=[];t=0
while t<T:
    if active[t]:
        s=t
        while t<T and active[t]: t+=1
        events.append({"onset":str(tgt_dt[s].date()),"end":str(tgt_dt[t-1].date())})
    else: t+=1
print(events)
print('MHW cell-days', mhw.sum(), 'active days', active.sum())