
Xt=X[tg_mask]; tdates=dates[tg_mask]; T=len(tdates)
sea=np.all(np.isfinite(Xt),axis=0)
doys=np.array([doy(t) for t in tdates])-1  # 0-based index into 366 arrays
thr_t=thr_s[doys]  # (T,ny,nx)
hot=(Xt>=thr_t)&sea[None]
mhw=np.zeros((T,ny,nx),bool)
def runs(b):
    # returns list of (start,end) inclusive for True runs
    d=np.diff(np.concatenate([[0],b.astype(np.int8),[0]]))
    s=np.where(d==1)[0]; e=np.where(d==-1)[0]-1
    return list(zip(s,e))
cnt_events=0
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        ev=[(s,e) for s,e in runs(hot[:,i,j]) if e-s+1>=5]
        if not ev: continue
        merged=[list(ev[0])]
        for s,e in ev[1:]:
            if s-merged[-1][1]-1<=2: merged[-1][1]=e
            else: merged.append([s,e])
        cnt_events+=len(merged)
        for s,e in merged: mhw[s:e+1,i,j]=True
print('per-cell events total', cnt_events, 'cell-days', mhw.sum())
active=mhw.any(axis=(1,2))
ev_reg=runs(active)
events=[{"onset":str(tdates[s].date()),"end":str(tdates[e].date())} for s,e in ev_reg]
print(events)
print('active days', active.sum())
