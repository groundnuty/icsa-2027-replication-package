import numpy as np, pandas as pd, time, warnings

t0 = time.time()
B = np.load("/work/B.npy")  # 4028 x 60 x 60 float64, 1991-12-27..2003-01-05
NI, NJ = B.shape[1], B.shape[2]
print("B loaded:", B.shape)

# doy per baseline date (leap scale; Feb29=60), core mask 1992..2002
read0 = pd.Timestamp("1991-12-27")
nd = B.shape[0]
dates = pd.date_range(read0, periods=nd, freq="D")
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
bdoy = cum[dates.month-1] + dates.day
core = np.array((dates >= pd.Timestamp("1992-01-01")) & (dates <= pd.Timestamp("2002-12-31")))

thr = np.full((366, NI, NJ), np.nan)
clim = np.full((366, NI, NJ), np.nan)
t1 = time.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for dd in range(1, 367):
        if dd == 60: continue
        centers = np.where(core & (bdoy == dd))[0]
        pos = np.concatenate([np.arange(c-5, c+6) for c in centers])
        pool = B[pos]
        thr[dd-1] = np.nanquantile(pool, 0.9, axis=0, method="hazen")
        clim[dd-1] = np.nanmean(pool, axis=0)
print("pool loop", round(time.time()-t1,1), "s")
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def circ31(a):
    out = np.zeros_like(a)
    for o in range(-15, 16):
        out += np.roll(a, -o, axis=0)
    return out/31.0
thr_s = circ31(thr); clim_s = circ31(clim)
np.savez("/work/thr_clim.npz", thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s)
print("saved; total", round(time.time()-t0,1), "s")

# quick sanity prints
print("thr_s range:", round(float(np.nanmin(thr_s)),3), round(float(npnanmax:=np.nanmax(thr_s)),3))
# spot-check a sea cell vs brute force at a few doys
sea = np.isfinite(B).all(axis=0)
print("sea cells (all baseline days finite):", int(sea.sum()), "of", NI*NJ)
ci, cj = np.argwhere(sea)[0]
bpos = pd.Series(np.arange(nd), index=dates)
for dd in [1, 152, 243, 365, 366]:
    md = dates[core & (bdoy == dd)]
    dset = set()
    for c in md:
        for o in range(-5, 6):
            dset.add(c + pd.Timedelta(days=int(o)))
    posb = np.sort(np.array([(dt-read0).days for dt in sorted(dset)]))
    v = B[posb, ci, cj]
    q = np.quantile(v[np.isfinite(v)], 0.9, method="hazen")
    mu = float(np.nanmean(v))
    print(f"doy {dd:3d}: q_match={np.isclose(q, thr[dd-1,ci,cj], rtol=0, atol=1e-12)} mean_match={np.isclose(mu, clim[dd-1,ci,cj], rtol=0, atol=1e-12)} n={len(posb)}")
# day-60 imputation and circular smoothing re-check
for dd in [1, 152, 243, 365, 366, 60]:
    doys = ((dd-1 + np.arange(-15,16)) % 366)
    print(f"smooth thr doy {dd:3d}: match={np.isclose(thr[doys,ci,cj].mean(), thr_s[dd-1,ci,cj], rtol=0, atol=1e-12)}")
print("d60 imputed:", bool(np.allclose(thr[59], 0.5*(thr[58]+thr[60])) and np.allclose(clim[59], 0.5*(clim[58]+clim[60]))))
