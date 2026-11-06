import numpy as np, datetime as dt, os, time, pickle
t0 = time.time()
OUT = "/work/mhw"

base = np.concatenate([np.load(f"{OUT}/base_{a:04d}_{b:04d}.npy") for a,b in
                       [(0,500),(500,1000),(1000,1500),(1500,2000),(2000,2500),(2500,3300),(3300,4028)]], axis=0)
tgt  = np.load(f"{OUT}/tgt_0000_0092.npy")
base_dates = [dt.date(1991,12,27) + dt.timedelta(days=k) for k in range(4028)]
tgt_dates  = [dt.date(2004,6,1) + dt.timedelta(days=k) for k in range(92)]

mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mcum = [0] + list(np.cumsum(mlen))
def doy(d): return mcum[d.month-1] + d.day

idx_of = {d: k for k, d in enumerate(base_dates)}
pools = {}
for d in base_dates:
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        dd = doy(d)
        if dd == 60: continue
        for k in range(-5,6):
            pools.setdefault(dd, []).append(idx_of[d + dt.timedelta(days=k)])
assert len(pools) == 365 and all(len(v)==121 for v in pools.values())

finite_all = np.all(np.isfinite(tgt), axis=0)
sea = np.argwhere(finite_all)
nsea = sea.shape[0]
cell_flat = sea[:,0]*60 + sea[:,1]
print("sea cells:", nsea, "land/missing:", 3600-nsea)

base_flat = base.reshape(4028, 3600)
thr  = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    V = base_flat[pools[dd]][:, cell_flat]
    thr[dd-1]  = np.nanquantile(V, 0.90, axis=0, method="hazen")
    clim[dd-1] = np.nanmean(V, axis=0)
thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("NaNs in thr/clim:", np.isnan(thr).any(), np.isnan(clim).any())

def smooth31(A):
    ext = np.concatenate([A, A, A], axis=0)
    C = np.empty((1099, A.shape[1]), dtype=np.float64)
    C[0] = 0.0
    np.cumsum(ext, axis=0, out=C[1:])
    s0 = 366 - 15
    return (C[s0+31 : s0+31+366] - C[s0 : s0+366]) / 31.0

thr_s  = smooth31(thr)
clim_s = smooth31(clim)

# ---- independent verification of one (doy, cell) ----
dd = 186  # e.g. 4 July
r, c = sea[0]
# independent date list: July 4 of each baseline year +- 5 days
vals = []
for y in range(1992, 2003):
    a = dt.date(y, 7, 4)
    for k in range(-5,6):
        t = a + dt.timedelta(days=k)
        ki = idx_of[t]
        vals.append(base[ki, r, c])
vals = np.array(vals, dtype=np.float64)
print("indep doy186 cell(%d,%d): thr=%.9f (mine %.9f) clim=%.9f (mine %.9f)"
      % (r, c, np.quantile(vals, 0.9, method="hazen"), thr[185,0],
         np.mean(vals), clim[185,0]))
assert np.isclose(np.quantile(vals,0.9,method="hazen"), thr[185,0], rtol=0, atol=1e-12)
assert np.isclose(np.mean(vals), clim[185,0], rtol=0, atol=1e-12)

# check a doy<60 (Jan 1 -> pool includes 1991-12-27..31) and doy 59/61 boundary
for dd2, md in [(1,(1,1)), (59,(2,28)), (61,(3,1))]:
    vals = []
    for y in range(1992,2003):
        a = dt.date(y, md[0], md[1])
        for k in range(-5,6):
            vals.append(base[idx_of[a+dt.timedelta(days=k)], r, c])
    vals = np.array(vals)
    assert np.isclose(np.quantile(vals,0.9,method="hazen"), thr[dd2-1,0], rtol=0, atol=1e-12)
    print("doy", dd2, "ok")

print("independent checks passed")
np.savez(f"{OUT}/results1.npz", thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s,
         sea_r=sea[:,0], sea_c=sea[:,1],
         tgt_dates=np.array(tgt_dates, dtype="datetime64[D]"))
print("saved results1.npz, elapsed %.1fs" % (time.time()-t0))
