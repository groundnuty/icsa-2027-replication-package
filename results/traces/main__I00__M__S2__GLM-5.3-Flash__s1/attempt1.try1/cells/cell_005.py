import numpy as np, pandas as pd, xarray as xr, pickle, os, time

t0 = time.time()
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

times = pd.to_datetime(ds.time.values)
tss = times.strftime("%Y-%m-%d")
idx = {s: i for i, s in enumerate(tss)}

lat = ds.latitude.values.astype("float64")
lon = ds.longitude.values.astype("float64")
lat_sel = np.where((lat >= 54.13) & (lat <= 55.33))[0]
lon_sel = np.where((lon >= 14.67) & (lon <= 15.87))[0]
assert lat_sel.min() >= 0 and lon_sel.min() >= 0, "region not found"

# Build the union date list with full pool structure
dates = {}
for y in range(1991, 2004):
    nd = 366 if calendar.isleap(y) else 365
    dates.update({f"{y}-{m:02d}-{d:02d}": (y, m, d) for m, d in calendar_days(y)})
for m, d in TARGET_DAYS:
    dates[f"2004-{m:02d}-{d:02d}"] = (2004, m, d)

def doy(m, d):
    return DOW[m, d]

# reverse map (doy, year)->date string
rmap = {}
for s, (y, m, d) in dates.items():
    rmap[(doy(m, d), y)] = s
for y in range(1991, 2004):
    nd = 366 if calendar.isleap(y) else 365
    for dd in range(1, nd+1):
        assert (dd, y) in rmap, (dd, y)

# windows: for each doy 1..366, set of baseline dates in union
win = []
for dd in range(1, 367):
    if dd == 60:
        win.append(None); continue
    base = []
    for y in range(1992, 2003):
        cand = []
        if dd == 1:
            if y-1 == 1991:
                cand += [rmap[(366, 1991)]]
        elif dd == 2:
            if y-1 == 1991:
                cand += [rmap[(366, 1991)], rmap[(1, 1991)]]
        elif dd <= 61:
            for e in range(dd-5, dd+6):
                if e >= 1 and e <= (366 if calendar.isleap(y-1) else 365):
                    cand.append(rmap[(e, y-1)])
        for e in range(max(1, dd-5), min(366, dd+5)+1):
            if e <= (366 if calendar.isleap(y) else 365):
                cand.append(rmap[(e, y)])
        base += cand
    win.append(sorted(set(base)))

# ordering: baseline+early, then target
ordered = [f"{y}-{m:02d}-{d:02d}" for (y, m, d) in
           sorted(dates.values(), key=lambda t: (t[0], t[1], t[2]))]
# sorted by (y,m,d) string sort works too since zero-padded; but years interleaved fine
time_indices = np.array([idx[s] for s in ordered], dtype="int64")
n_ext = len(ordered)
print("extension days:", n_ext, "first:", ordered[0], "last:", ordered[-1])

# target absolute positions
targ_abs = {}
for m, d in TARGET_DAYS:
    targ_abs[(2004, m, d)] = ordered.index(f"2004-{m:02d}-{d:02d}")
tgt_pos = np.array(sorted(targ_abs.values()))
print("target span abs:", tgt_pos.min(), "->", tgt_pos.max())

# doy per extension day
doy_ext = np.array([doy(m, d) for (y, m, d) in (dates[s] for s in ordered)], dtype="int64")
# is a given extension day in window of doy dd?
in_win = np.zeros((367, n_ext), dtype=bool)
for dd in range(1, 367):
    if dd == 60: continue
    for s in win[dd-1]:
        in_win[dd, ordered.index(s)] = True
print("window sizes min/max:", in_win[1].sum(), in_win[[d for d in range(1,367) if d!=60]].max())

# read data
print("reading SST cube ...", time.time()-t0)
sst = ds.analysed_sst.isel(time=time_indices, latitude=lat_sel, longitude=lon_sel).values.astype("float64")
print("cube:", sst.shape, "read done", time.time()-t0)

np.save("/tmp/mhw_work/sst.npy", sst.astype("float32"))
np.save("/tmp/mhw_work/in_win.npy", in_win)
np.save("/tmp/mhw_work/doy_ext.npy", doy_ext)
np.save("/tmp/mhw_work/tgt_pos.npy", tgt_pos)
with open("/tmp/mhw_work/ordered.pkl", "wb") as f:
    pickle.dump({"ordered": ordered, "lat_sel": lat_sel, "lon_sel": lon_sel,
                 "lat_vals": lat[lat_sel], "lon_vals": lon[lon_sel]}, f)

# sea cell diagnostics
finite_all = np.isfinite(sst[tgt_pos]).all(axis=0)
nan_days_cnt = np.isnan(sst[tgt_pos]).sum(axis=0)
print("cells:", sst.shape[1]*sst.shape[2], "all-finite target:", finite_all.sum())
print("nan-days count distribution over cells (target):",
      dict(zip(*np.unique(nan_days_cnt, return_counts=True))))
print("baseline any-finite cells:", np.isfinite(sst[:8422]).any(axis=0).sum())
print("elapsed", time.time()-t0)
