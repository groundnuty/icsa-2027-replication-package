import numpy as np, datetime as dt, os, time
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

# sea cells
finite_all = np.all(np.isfinite(tgt), axis=0)   # (60,60)
sea = np.argwhere(finite_all)
nsea = sea.shape[0]
cell_flat = sea[:,0]*60 + sea[:,1]
print("sea cells:", nsea, "land/missing:", 3600-nsea)

base_flat = base.reshape(4028, 3600)
thr  = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    V = base_flat[pools[dd]][:, cell_flat]          # (121, nsea)
    thr[dd-1]  = np.nanquantile(V, 0.90, axis=0, method="hazen")
    clim[dd-1] = np.nanmean(V, axis=0)

# day 60 fill
thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("any NaN in thr/clim after fill:", np.isnan(thr).any(), np.isnan(clim).any())
print("thr range:", np.nanmin(thr), np.nanmax(thr))

# smooth: 366-element arrays, centred 31-day moving mean, wrap
def smooth31(A):  # A: (366, n)
    ext = np.concatenate([A, A, A], axis=0)   # (1098, n)
    C = np.empty((1099, A.shape[1]), dtype=np.float64)
    C[0] = 0.0
    np.cumsum(ext, axis=0, out=C[1:])
    # for day index i (0..365): sum of ext[i-15 .. i+15] = ext[i-15+1 .. i+15+1] in cumsum terms
    # use middle copy: indices 366-15+i .. 366-15+i+30
    s0 = 366 - 15
    S = C[s0+31 : s0+31+366] - C[s0 : s0+366]
    return S / 31.0

thr_s  = smooth31(thr)
clim_s = smooth31(clim)
print("smoothed thr range:", thr_s.min(), thr_s.max(), "NaNs:", np.isnan(thr_s).any())

# sanity: verify smooth31 on a synthetic array incl. wrap
A = np.arange(366, dtype=np.float64)[:,None]
S = smooth31(A)
# day i (0-based): mean of (i-15..i+15) mod 366. For i in 15..350: mean = i (symmetric). Check a few.
for i in [15, 100, 350]:
    assert abs(S[i,0] - i) < 1e-9, (i, S[i,0])
# i=0: days 351..365 and 0..14 -> mean of those 31 values
exp0 = (np.arange(351,366).sum() + np.arange(0,15).sum())/31
assert abs(S[0,0]-exp0) < 1e-9, (S[0,0], exp0)
i=365: pass
exp365 = (np.arange(350,366).sum() + np.arange(0,1).sum())/31
assert abs(S[365,0]-exp365) < 1e-9, (S[365,0], exp365)
print("smooth31 verified")

np.savez(f"{OUT}/results1.npz", thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s,
         sea_r=sea[:,0], sea_c=sea[:,1],
         tgt_dates=np.array(tgt_dates, dtype="datetime64[D]"))
print("saved. elapsed %.1fs" % (time.time()-t0))
