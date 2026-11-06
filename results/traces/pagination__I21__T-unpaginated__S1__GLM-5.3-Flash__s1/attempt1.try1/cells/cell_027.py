import xarray as xr, numpy as np, json, datetime as dt

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw']
print("dtype:", m.dtype, "| dims:", m.dims, "| shape:", m.shape)
print("unique values:", np.unique(m.values), "| mhw cell-days:", int(m.values.sum()))
print("time range:", str(ds.time.values[0])[:10], "->", str(ds.time.values[-1])[:10], "n =", ds.time.size)
print("lat range: %.4f .. %.4f | lon range: %.4f .. %.4f" % (ds.lat.values[0], ds.lat.values[-1], ds.lon.values[0], ds.lon.values[-1]))

# consistency: mask re-derived from stored arrays
thr = np.load('/tmp/thr_s.npy'); tgt = np.load('/tmp/tgt_cube.npy')
def mdoy(d): return (dt.date(2000,d.month,d.day)-dt.date(2000,1,1)).days+1
tgt_days = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
tdoy = np.array([mdoy(d) for d in tgt_days])
sea = np.isfinite(tgt).all(axis=0)
hot = (tgt >= thr[tdoy]) & sea
mhw2 = np.zeros((92,60,60), bool)
def mhw_from_hot(h, nT, minlen=5, gap=2):
    runs=[]; t=0
    while t < nT:
        if h[t]:
            s=t
            while t<nT and h[t]: t+=1
            runs.append([s,t-1])
        else: t+=1
    g=[]
    for r in runs:
        if g and r[0]-g[-1][1]-1<=gap: g[-1][1]=r[1]
        else: g.append(list(r))
    for s,e in g:
        if e-s+1>=minlen: m[s:e+1]=True
    return m
for i in range(60):
    for j in range(60):
        if sea[i,j]:
            mm = np.zeros(92,bool); mhw_from_hot(hot[:,i,j],92) if False else None
            g=[]; h=hot[:,i,j]; t=0
            while t<92:
                if h[t]:
                    s=t
                    while t<92 and h[t]: t+=1
                    r=[s,t-1]
                    if g and r[0]-g[-1][1]-1<=2: g[-1][1]=r[1]
                    else: g.append(r)
                else: t+=1
            for s,e in g:
                if e-s+1>=5: mm[s:e+1]=True
            mhw2[:,i,j]=mm
print("stored mask == recomputed mask:", np.array_equal(m.values.astype(bool), mhw2))
act = mhw2.sum(axis=(1,2))>0
evs=[]; t=0
while t<92:
    if act[t]:
        s=t
        while t<92 and act[t]: t+=1
        evs.append((tgt_days[s].isoformat(), tgt_days[t-1].isoformat()))
    else: t+=1

rep = json.load(open('output/report.json'))
print("report keys:", sorted(rep.keys()))
print("events in report match recomputed:", rep['events'] == [{"onset":a,"end":b} for a,b in evs])
print("region:", rep['region'], "| baseline:", rep['baseline_analysed'], "| target:", rep['target_analysed'])
print("complete:", rep['complete'], "| caveats:", repr(rep['caveats']))
print("ALL CHECKS DONE")
