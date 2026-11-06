import numpy as np, pandas as pd, h5py, os, warnings, time
import xarray as xr

p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
I0, I1, J0, J1 = 182, 241, 690, 749
NI, NJ = I1-I0+1, J1-J0+1
t0 = time.time()

ds = xr.open_dataset(p, engine="h5netcdf")
times = pd.DatetimeIndex(ds["time"].values)
bidx = np.where((times >= "1991-12-27") & (times <= "2003-01-05"))[0]
bdates = times[bidx]
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # cumulative days, leap scale (29 Feb=60)
bdoy = cum[bdates.month-1] + bdates.day
print("baseline span:", bdates[0].date(), "->", bdates[-1].date(), "n =", len(bidx))

f = h5py.File(p, "r"); dvar = f["analysed_sst"]
B = np.empty((len(bidx), NI, NJ), dtype="float64")
for s in range(0, len(bidx), 250):
    e = min(s+250, len(bidx))
    B[s:e] = dvar[bidx[s]:bidx[e], I0:I1+1, J0:J1+1].astype("float64")
f.close()
print("baseline read", round(time.time()-t0,1), "s; finite frac", round(float(np.isfinite(B).mean()),4))

groups = {}
for k, dd in enumerate(bdoy):
    groups.setdefault(int(dd), []).append(k)
gidx = {k: np.array(v) for k, v in groups.items()}
print("doy groups: n doys", len(gidx), "min/max pool size per doy-year",
      min(len(v) for v in gidx.values()), max(len(v) for v in gidx.values()))

thr = np.full((366, NI, NJ), np.nan)
clim = np.full((366, NI, NJ), np.nan)
t1 = time.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for dd in range(1, 367):
        if dd == 60: continue
        w = np.array([((dd-1+o) % 366) + 1 for o in range(-5, 6)])
        pos = np.concatenate([gidx[int(x)] for x in w])
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
print("saved intermediates; total", round(time.time()-t0,1), "s")

# ---- brute-force validation of pool logic via calendar arithmetic ----
sea_guess = np.isfinite(B).all(axis=0)
ci, cj = np.argwhere(sea_guess)[0]
print("validation cell (local idx):", ci, cj, "finite all baseline days:", bool(sea_guess[ci,cj]))
bpos = pd.Series(np.arange(len(bdates)), index=bdates)
def brute(ddo):
    md = bdates[bdoy == ddo]
    dates = set()
    for y in sorted(set(md.year)):
        c = pd.Timestamp(year=int(y), month=int(md[0].month), day=int(md[0].day))
        for o in range(-5, 6):
            dates.add(c + pd.Timedelta(days=o))
    return bpos.loc[sorted(dates)].values
ok = True
for ddo in [1, 3, 5, 58, 59, 60, 61, 101, 152, 200, 243, 356, 357, 366]:
    if ddo == 60: continue
    pos = brute(ddo)
    v = B[pos, ci, cj]
    q = np.quantile(v[np.isfinite(v)], 0.9, method="hazen")
    mu = float(np.nanmean(v))
    okq = np.isclose(q, thr[ddo-1, ci, cj], rtol=0, atol=1e-12)
    okm = np.isclose(mu, clim[ddo-1, ci, cj], rtol=0, atol=1e-12)
    ok &= okq and okm
    print(f"doy {ddo:3d}: pool n={len(pos):3d} q_match={okq} mean_match={okm}")
# smoothing validation (direct modular average)
for ddo in [1, 3, 60, 101, 200, 366]:
    doys = ((ddo-1 + np.arange(-15,16)) % 366)
    m = thr[doys, ci, cj].mean()
    print(f"smooth doy {ddo:3d}: match={np.isclose(m, thr_s[ddo-1, ci, cj], rtol=0, atol=1e-12)}")
# day-60 imputation check
print("day60 imputed:", np.allclose(thr[59], 0.5*(thr[58]+thr[60])), np.allclose(clim[59], 0.5*(clim[58]+clim[60])))
print("ALL VALIDATION OK:", bool(ok))
