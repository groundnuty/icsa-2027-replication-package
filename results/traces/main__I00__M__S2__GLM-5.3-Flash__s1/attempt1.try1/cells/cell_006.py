import numpy as np, pandas as pd, xarray as xr, pickle, os, time, calendar

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

# Build the union date list
DOW = np.zeros((13, 32), dtype=int)
for m in range(1, 13):
    ndays = [31,29,31,30,31,30,31,31,30,31,30,31][m-1]
    for d in range(1, ndays+1):
        DOW[m, d] = sum([31,29,31,30,31,30,31,31,30,31,30,31][:m-1]) + d

TARGET_DAYS = [(6,m) for m in range(1,31)] + [(7,m) for m in range(1,32)] + [(8,m) for m in range(1,32)]
TARGET_DAYS = [(6,m) for m in range(1,31)] + [(7,m) for m in range(1,32)] + [(8,m) for m in range(1,32)]

dates = {}
for y in range(1991, 2004):
    nd = 366 if calendar.isleap(y) else 365
    for dd in range(1, nd+1):
        dates[f"{y}-{m:02d}-{d:02d}"] = None  # placeholder, will redo properly

# redo properly: iterate days via datetime
import datetime as dtm
d0 = dtm.date(1991,1,1); d1 = dtm.date(2003,12,31)
dates = {}
s = d0
while s <= d1:
    dates[s.strftime("%Y-%m-%d")] = (s.year, s.month, s.day)
    s += dtm.timedelta(days=1)
for m, d in [(6,m) for m in range(1,31)] + [(7,m) for m in range(1,32)] + [(8,m) for m in range(1,32)]:
    dates[f"2004-{m:02d}-{d:02d}"] = (2004, m, d)

def doy_of(y, m, d):
    return DOW[m, d]

rmap = {}
for k, (y, m, d) in dates.items():
    rmap[(doy_of(y, m, d), y)] = k
for y in range(1991, 2004):
    nd = 366 if calendar.isleap(y) else 365
    for dd in range(1, nd+1):
        assert (dd, y) in rmap, (dd, y)

# windows for each doy
win = []
for dd in range(1, 367):
    if dd == 60:
        win.append(None); continue
    base = []
    for y in range(1992, 2003):
        if dd == 1:
            if y-1 == 1991:
                base.append(rmap[(366, 1991)])
        elif dd == 2:
            if y-1 == 1991:
                base += [rmap[(366, 1991)], rmap[(1, 1991)]]
        elif dd <= 61:
            for e in range(dd-5, dd+6):
                if e >= 1 and e <= (366 if calendar.isleap(y-1) else 365):
                    base.append(rmap[(e, y-1)])
        for e in range(max(1, dd-5), min(366, dd+5)+1):
            if e <= (366 if calendar.islead if False else (366 if calendar.isleap(y) else 365)):
                pass
    win.append(sorted(set(base)))
# fix the last loop (buggy attempt)
win = []
for dd in range(1, 367):
    if dd == 60:
        win.append(None); continue
    base = []
    for y in range(1992, 2003):
        if dd == 1:
            if y-1 == 1991:
                base.append(rmap[(366, 1991)])
        elif dd == 2:
            if y-1 == 1991:
                base += [rmap[(366, 1991)], rmap[(1, 1991)]]
        elif dd <= 61:
            for e in range(dd-5, dd+5+1):
                if 1 <= e <= (366 if calendar.isleap(y-1) else 365):
                    base.append(rmap[(e, y-1)])
        for e in range(max(1, dd-5), min(366, dd+5)+1):
            if e <= (366 if calendar.isleap(y) else 365):
                base.append(rmap[(e, y)])
    win.append(sorted(set(base)))

ordered = sorted(dates.keys())
time_indices = np.array([idx[s] for s in ordered], dtype="int64")
n_ext = len(ordered)
print("extension days:", n_ext, "first:", ordered[0], "last:", ordered[-1])

targ_pos = np.array([ordered.index(f"2004-{m:02d}-{d:02d}") for m, d in
                     [(6,m) for m in range(1,31)] + [(7,m) for m in range(1,32)] + [(8,m) for m in range(1,32)]])
print("target span abs:", targ_pos.min(), "->", targ_pos.max())

doy_ext = np.array([doy_of(*dates[s]) for s in ordered], dtype="int64")

in_win = np.zeros((367, n_ext), dtype=bool)
for dd in range(1, 367):
    if dd == 60: continue
    for s in win[dd-1]:
        in_win[dd, ordered.index(s)] = True
sizes = in_win[[d for d in range(1,367) if d != 60]]
print("window sizes min/max/mean:", sizes.min(), sizes.max(), sizes.mean())

print("reading SST cube ...")
sst = ds.analysed_sst.isel(time=time_indices, latitude=lat_sel, longitude=lon_sel).values.astype("float64")
print("cube:", sst.shape, sst.dtype, "read done", time.time()-t0)

np.save("/tmp/mhw_work/sst.npy", sst.astype("float32"))
np.save("/tmp/mhw_work/in_win.npy", in_win)
np.save("/tmp/mhw_work/doy_ext.npy", doy_ext)
np.save("/tmp/mhw_work/targ_pos.npy", targ_pos)
with open("/tmp/mhw_work/ordered.pkl", "wb") as f:
    pickle.dump({"ordered": ordered, "lat_sel": lat_sel, "lon_sel": lon_sel,
                 "lat_vals": lat[lat_sel].astype("float64"),
                 "lon_vals": lon[lon_sel].astype("float64")}, f)

finite_all = np.isfinite(sst[targ_pos]).all(axis=0)
nan_days_cnt = np.isnan(sst[targ_pos]).sum(axis=0)
print("cells:", sst.shape[1]*sst.shape[2], "all-finite target:", finite_all.sum())
print("nan-days histogram (target):", dict(zip(*np.unique(nan_days_cnt, return_counts=True))))
print("baseline any-finite cells:", np.isfinite(sst[:targ_pos.min()]).any(axis=0).sum())
print("elapsed", time.time()-t0)
