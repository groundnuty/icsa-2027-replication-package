import numpy as np, datetime as dt
tdata=np.load('/tmp/target.npy').astype(np.float64)
tdates=[dt.date(2004,6,1)+dt.timedelta(days=i) for i in range(tdata.shape[0])]
tdoy=np.array([(d-dt.date(d.year,1,1)).days+1 for d in tdates])
thr_sm=np.load('/tmp/thr_sm.npy')
sea=np.isfinite(tdata).all(axis=0)
hot=tdata>=thr_sm[tdoy-1]
hot&=sea[None,:,:]

def max_run(h):
    best=0; cur=0
    for x in h:
        cur = cur+1 if x else 0
        best=max(best,cur)
    return best

runs={}
cells_with_runs=[]
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        m=max_run(hot[:,i,j])
        runs[m]=runs.get(m,0)+1
        if m>=3: cells_with_runs.append(((i,j),m))
print("distribution of max consecutive-hot-run length per sea cell:", dict(sorted(runs.items())))
print("cells with runs >=3:", len(cells_with_runs))
print(sorted(cells_with_runs, key=lambda x:-x[1])[:15])
# hot-day count per day around the peak
hpd=hot.reshape(tdata.shape[0],-1).sum(axis=1)
for t in range(tdata.shape[0]):
    if hpd[t]>0:
        print(tdates[t], int(hpd[t]))
