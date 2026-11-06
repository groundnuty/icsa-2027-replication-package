import numpy as np, pandas as pd, h5py, time, warnings, os, json
import xarray as xr

p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
I0, I1, J0, J1 = 182, 241, 690, 749
NI, NJ = I1-I0+1, J1-J0+1
t0 = time.time()

z = np.load("/work/thr_clim.npz")
thr_s, clim_s = z["thr_s"], z["clim_s"]
# confirm land-cell NaN explanation for the earlier allclose=False
thr, clim = z["thr"], z["clim"]
print("d60 imputed (finite elems):",
      bool(np.allclose(thr[59][np.isfinite(thr[59])], 0.5*(thr[58]+thr[60])[np.isfinite(thr[59])], rtol=0, atol=1e-12)),
      "| any NaN in thr:", bool(np.isnan(thr).any()), "| NaN cells:", int(np.isnan(thr[151]).sum()))

ds = xr.open_dataset(p, engine="h5netcdf")
times = pd.DatetimeIndex(ds["time"].values)
ti = np.where((times >= "2014-06-01") & (times <= "2014-08-31"))[0]
tdates = times[ti]
print("target days:", len(ti), tdates[0].date(), "->", tdates[-1].date(), "contiguous:", bool(np.all(np.diff(ti)==1)))
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
tdoy = cum[tdates.month-1] + tdates.day
print("target doys:", tdoy[0], "..", tdoy[-1])

f = h5py.File(p, "r"); dvar = f["analysed_sst"]
SST = dvar[ti[0]:ti[-1]+1, I0:I1+1, J0:J1+1].astype("float64")
f.close()
print("target read", round(time.time()-t0,1), "s; finite frac", round(float(np.isfinite(SST).mean()),4))

sea = np.isfinite(SST).all(axis=0)          # finite every target day
print("sea cells:", int(sea.sum()), "of", NI*NJ)

T = len(ti)
thr_day = thr_s[tdoy-1]                      # (T, NI, NJ)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    hot = SST >= thr_day
hot[~sea] = False
print("hot frac over sea cells:", round(float(hot[:, sea].mean()), 4))

def runs_of(h):  # h: (T,) bool -> list of (start, end) inclusive
    hh = h.astype(np.int8)
    d = np.diff(hh)
    starts = list(np.where(d == 1)[0] + 1); ends = list(np.where(d == -1)[0])
    if hh[0] == 1: starts = [0] + starts
    if hh[-1] == 1: ends = ends + [T-1]
    return list(zip(starts, ends))

mhw = np.zeros((T, NI, NJ), dtype=bool)
n_events_tot = 0
n_joined = 0
for ci in range(NI):
    for cj in range(NJ):
        kept = [(s, e) for (s, e) in runs_of(hot[:, ci, cj]) if e - s + 1 >= 5]
        if not kept: continue
        events = []
        for (s, e) in kept:
            if events and (s - events[-1][1] - 1) <= 2:
                n_joined += 1
                events[-1] = (events[-1][0], e)
            else:
                events.append((s, e))
        n_events_tot += len(events)
        for (s, e) in events:
            mhw[s:e+1, ci, cj] = True
print("per-cell MHW events:", n_events_tot, "| joins performed:", n_joined)
print("per-cell MHW days total:", int(mhw.sum()))

active = mhw[:, sea].any(axis=1)
print("active days:", int(active.sum()), "of", T)
reg_events = [(s, e) for (s, e) in runs_of(active)]
print("regional events:", len(reg_events))
for (s, e) in reg_events:
    ncell = int(mhw[s:e+1].any(axis=0).sum())
    print(f"  {tdates[s].date()} .. {tdates[e].date()}  ({e-s+1} d, cells in MHW: {ncell})")

np.save("/work/mhw.npy", mhw)
print("done", round(time.time()-t0,1), "s")
