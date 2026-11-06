
import json, time
import numpy as np
import xarray as xr

X_tgt = np.load("/tmp/X_tgt.npy"); sea2 = np.load("/tmp/sea2.npy")
thrS = np.load("/tmp/thrS.npy"); climS = np.load("/tmp/climS.npy")
t = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf").time.values
t_tgt = t[10378:10470]
si = np.argwhere(sea2); n_sea = si.shape[0]

# daily diagnostics
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mdoy = np.zeros((12,31), int)
off = 0
for m in range(12):
    mdoy[m, :mlen[m]] = off + 1 + np.arange(mlen[m]); off += mlen[m]
def md_of(dt):
    mo = int(np.datetime64(dt,'M').astype(np.int64)) % 12
    day = int(np.datetime64(dt,'D').astype(np.int64) - np.datetime64(np.datetime64(dt,'M'),'D').astype(np.int64)) + 1
    return mo, day
doy_t = np.array([mdoy[md_of(dt)[0], md_of(dt)[1]-1] for dt in t_tgt])
hot = X_tgt >= thrS[:, doy_t-1].T

# per-cell MHW (same algorithm, vectorised differently for cross-check)
def cell_mhw(h):
    # morphological cross-check: dilate gap of <=2 between kept runs
    out = np.zeros_like(h, bool)
    # find runs
    d = np.diff(np.concatenate(([0], h, [0])))
    s = np.flatnonzero(d==1); e = np.flatnonzero(d==-1)-1
    keep = s[(e-s+1) >= 5]
    ee = e[(e-s+1) >= 5]
    cur = None
    ivs = []
    for a,b in zip(keep, ee):
        if cur is not None and a - cur[1] - 1 <= 2:
            cur = (cur[0], b)
        else:
            if cur: ivs.append(cur)
            cur = (a,b)
    if cur: ivs.append(cur)
    for a,b in ivs: out[a:b+1] = True
    return out, ivs

t0=time.time()
res = np.array([cell_mhw(hot[:,c])[0] for c in range(n_sea)]).T  # (92, n_sea)
print("mhw cross-check done", round(time.time()-t0,1),"s")
active = res.any(axis=1)
da = np.diff(np.concatenate(([0], active, [0])))
es = np.flatnonzero(da==1); ee2 = np.flatnonzero(da==-1)-1
print("events:", [(str(np.datetime64(t_tgt[a],'D')), str(np.datetime64(t_tgt[b],'D'))) for a,b in zip(es,ee2)])
cnt = res.sum(axis=1)
print("per-day MHW cell counts (first/last of event):")
for i in np.where(active)[0]:
    if i in (0,1,2,3,4,5) or i >= len(t_tgt)-6:
        print(" ", np.datetime64(t_tgt[i],'D'), int(cnt[i]))
print("min/max MHW cells on active days:", int(cnt[active].min()), int(cnt[active].max()))
nonactive = np.where(~active)[0]
print("non-active days:", [str(np.datetime64(t_tgt[i],'D')) for i in nonactive])
