
import numpy as np, xarray as xr, datetime as dtm
X_tgt = np.load("/tmp/X_tgt.npy"); sea2 = np.load("/tmp/sea2.npy")
thrS = np.load("/tmp/thrS.npy")
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
t = ds.time.values
t_tgt = t[10378:10470]
si = np.argwhere(sea2); n_sea = si.shape[0]

# 1) determine numpy 'hazen' formula empirically
for n in (3, 5, 10, 20, 121):
    v = np.arange(1, n+1, dtype=float)
    q = float(np.quantile(v, 0.9, method="hazen"))
    h = n*0.9 + 0.5
    lo = int(np.floor(h)); frac = h - lo
    pred = v[-1] if lo >= n else v[lo-1] + frac*(v[lo]-v[lo-1])
    print(n, "numpy", q, "manual(n*.9+.5)", pred, "match", np.isclose(q, pred))

mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mdoy = np.zeros((12,31), int)
off=0
for m in range(12):
    mdoy[m,:mlen[m]] = off+1+np.arange(mlen[m]); off += mlen[m]
def md_of(dt):
    mo = int(np.datetime64(dt,'M').astype(np.int64))%12
    day = int(np.datetime64(dt,'D').astype(np.int64)-np.datetime64(np.datetime64(dt,'M'),'D').astype(np.int64))+1
    return mo, day
doy_t = np.array([mdoy[md_of(dt)[0], md_of(dt)[1]-1] for dt in t_tgt])
hot = X_tgt >= thrS[:, doy_t-1].T

def cell_mhw(h):
    out = np.zeros_like(h, bool)
    d = np.diff(np.concatenate(([0], h, [0])))
    s = np.flatnonzero(d==1); e = np.flatnonzero(d==-1)-1
    keep = (e-s+1) >= 5
    cur=None; ivs=[]
    for a,b in zip(s[keep], e[keep]):
        if cur is not None and a-cur[1]-1 <= 2: cur=(cur[0], b)
        else:
            if cur: ivs.append(cur)
            cur=(a,b)
    if cur: ivs.append(cur)
    for a,b in ivs: out[a:b+1]=True
    return out
res = np.stack([cell_mhw(hot[:,c]) for c in range(n_sea)], axis=1)
cnt = res.sum(axis=1)
act = np.where(cnt>0)[0]
print("active day counts:")
print(" ".join(f"{str(np.datetime64(t_tgt[i],'D'))[5:]}:{int(cnt[i])}" for i in act))
