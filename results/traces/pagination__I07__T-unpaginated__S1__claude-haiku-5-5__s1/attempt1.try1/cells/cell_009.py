tm=(dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
tdates=dates[tm]; tsst=sst64[tm]; tdoy=doys[tm]
T=thr_s[tdoy-1]  # shape (nt,60,60)
with np.errstate(invalid='ignore'):
    hot=(tsst>=T)
hot&=sea[None]
nt=len(tdates)
mhw=np.zeros((nt,60,60),bool)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs
        runs=[]; s=None
        for t in range(nt+1):
            v=h[t] if t<nt else False
            if v and s is None: s=t
            if not v and s is not None:
                if t-s>=5: runs.append([s,t-1])
                s=None
        if not runs: continue
        # join gaps of 1 or 2 non-hot days
        merged=[runs[0]]
        for r in runs[1:]:
            gap=r[0]-merged[-1][1]-1
            if gap<=2: merged[-1]=[merged[-1][0], r[1]]
            else: merged.append(r)
        for a,b in merged: mhw[a:b+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; s=None
for t in range(nt+1):
    v=active[t] if t<nt else False
    if v and s is None: s=t
    if not v and s is not None:
        events.append((str(tdates[s].date()), str(tdates[t-1].date()))); s=None
print('days active', active.sum(), 'cell-days', mhw.sum())
print(events)
