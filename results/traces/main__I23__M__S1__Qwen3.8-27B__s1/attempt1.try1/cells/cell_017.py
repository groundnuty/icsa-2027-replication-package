import numpy as np, json, datetime as dt
OUT="/tmp/mhw"
ext = np.load(f"{OUT}/ext.npy").reshape(4028, 3600)
dates = json.load(open(f"{OUT}/dates.json"))
ext_dates = [dt.date.fromisoformat(s) for s in dates["ext_dates"]]
MS = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doy = lambda d: MS[d.month-1]+d.day
base_dates = ext_dates[5:5+4018]
D_base = np.array([doy(b) for b in base_dates])
G = np.arange(4018)[:,None] + np.arange(11)[None,:]

c=12; d=153
rows = np.flatnonzero(D_base == d)
mask = np.zeros(4028, bool); mask[G[rows].ravel()] = True
pool = ext[np.flatnonzero(mask), c]
pool = pool[np.isfinite(pool)]
print("n:", len(pool))
q_np = np.nanquantile(pool, 0.9, method="hazen")
x = np.sort(pool); n=len(x); h=(n+1)*0.9; j=int(np.floor(h)); g=h-j
a=x[j-1]; b=x[j]
q_manual = a + g*(b-a)
print("np quantile:", repr(q_np))
print("manual:", repr(q_manual), "j:", j, "g:", g)
print("x[j-2:j+2]:", x[j-2:j+2])
# check the earlier naive value 286.407983398: what h would produce it?
# maybe the earlier naive pool had 120 values (one NaN)?
# recompute naive pool now
nvals=[]
for b in base_dates:
    if doy(b)!=d: continue
    for k in range(-5,6):
        t=b+dt.timedelta(days=k)
        i=ext_dates.index(t)
        v=ext[i,c]
        if np.isfinite(v): nvals.append(v)
print("naive n:", len(nvals))
qn = np.nanquantile(np.array(nvals), 0.9, method="hazen")
print("naive np quantile:", repr(qn))
print("pools identical:", np.allclose(np.sort(nvals), pool))
y=np.sort(nvals)
print("y[j-2:j+2]:", y[j-2:j+2])
# compare elementwise
d1 = np.abs(np.sort(nvals)-pool)
print("max abs diff:", d1.max())
# which positions differ
pos = np.flatnonzero(d1>1e-12)
print("diff positions:", pos[:20])
for p in pos[:5]:
    print("  vec", pool[p], "naive", np.sort(nvals)[p])
