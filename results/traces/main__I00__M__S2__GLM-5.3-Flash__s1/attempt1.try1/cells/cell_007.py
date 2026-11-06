script = r'''
import numpy as np, pandas as pd, xarray as xr, pickle, os, time, calendar, datetime as dtm

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

# day-of-year by month/day (leap-year style, 1..366)
MDAYS = [31,29,31,30,31,30,31,31,30,31,30,31]
CUM = [0]
for nd in MDAYS: CUM.append(CUM[-1]+nd)
def doy_of(m, d):
    return CUM[m-1] + d

target_md = [(6,m) for m in range(1,31)] + [(7,m) for m in range(1,32)] + [(8,m) for m in range(1,32)]

dates = {}
s = dtm.date(1991,1,1)
while s <= dtm.date(2003,12,31):
    dates[s.strftime("%Y-%m-%d")] = (s.year, s.month, s.day)
    s += dtm.timedelta(days=1)
for (m, d) in target_md:
    dates["2004-%02d-%02d" % (m, d)] = (2004, m, d)

rmap = {}
for k, (y, m, d) in dates.items():
    rmap[(doy_of(m, d), y)] = k
for y in range(1991, 2004):
    nd = 366 if calendar.isleap(y) else 365
    for dd in range(1, nd+1):
        assert (dd, y) in rmap, (dd, y)

# windows per doy
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
pos = {s: i for i, s in enumerate(ordered)}
time_indices = np.array([idx[s] for s in ordered], dtype="int64")
n_ext = len(ordered)
print("extension days:", n_ext, "first:", ordered[0], "last:", ordered[-1])

targ_pos = np.array([pos["2004-%02d-%02d" % (m, d)] for (m, d) in target_md])
print("target span abs:", targ_pos.min(), "->", targ_pos.max())

doy_ext = np.array([doy_of(*dates[s][1:]) for s in ordered], dtype="int64")

in_win = np.zeros((367, n_ext), dtype=bool)
for dd in range(1, 367):
    if dd == 60: continue
    for s in win[dd-1]:
        in_win[dd, pos[s]] = True
sizes = in_win[[d for d in range(1,367) if d != 60]]
print("window sizes min/max/mean:", sizes.min(), sizes.max(), round(sizes.mean(),1))

print("reading SST cube ...")
sst = ds.analysed_sst.isel(time=time_indices, latitude=lat_sel, longitude=lon_sel).values.astype("float64")
print("cube:", sst.shape, sst.dtype, "read done", time.time()-t0)

np.save("/tmp/mhw_work/sst.npy", sst.astype("float32"))
np.save("/tmp/mhw_work/in_win.npy", in_win)
np.save("/tmp/mhw_work/doy_ext.npy", doy_ext)
np.save("/tmp/mhw_work/targ_pos.npy", targ_pos)
with open("/tmp/mhw_work/meta.pkl", "wb") as f:
    pickle.dump({"ordered": ordered, "lat_sel": lat_sel, "lon_sel": lon_sel,
                 "lat_vals": lat[lat_sel].astype("float64"),
                 "lon_vals": lon[lon_sel].astype("float64"),
                 "target_md": target_md}, f)

finite_all = np.isfinite(sst[targ_pos]).all(axis=0)
nan_days_cnt = np.isnan(sst[targ_pos]).sum(axis=0)
print("cells:", sst.shape[1]*sst.shape[2], "all-finite target:", int(finite_all.sum()))
print("nan-days histogram (target):", dict(zip(*np.unique(nan_days_cnt, return_counts=True))))
print("baseline any-finite cells:", int(np.isfinite(sst[:targ_pos.min()]).any(axis=0).sum()))
print("elapsed", time.time()-t0)
'''
with open("/tmp/mhw_work/extract.py", "w") as f:
    f.write(script)
print("script written, length", len(script))
