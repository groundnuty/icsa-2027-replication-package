import numpy as np, datetime as dt

z = np.load("/work/cache_sst.npz"); ext32, tgt32 = z["ext"], z["tgt"]
ext_ord, tgt_ord = z["ext_ord"], z["tgt_ord"]
ext64 = ext32.astype(np.float64)
z2 = np.load("/work/cache_thr2.npz"); thr, clim, thr_raw, clim_raw = z2["thr"], z2["clim"], z2["thr_raw"], z2["clim_raw"]

ext_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in ext_ord], dtype=np.int32)
b_start = dt.date(1992,1,1).toordinal(); b_end = dt.date(2002,12,31).toordinal()
bmask = (ext_ord >= b_start) & (ext_ord <= b_end)
sea = np.all(np.isfinite(tgt32.astype(np.float64)), axis=0)

# --- Brute-force independent pool check for several doys & cells ---
D = "/data/icsa2027_data_20261101T090944Z/s1z"
import xarray as xr
def load_range(o1, o2):
    out, ords = [], []
    cur = dt.date.fromordinal(int(o1))
    while cur.toordinal() <= o2:
        ds = xr.open_dataset(f"{D}/sst_{cur:%Y%m%d}.nc", engine="h5netcdf")
        out.append(ds["analysed_sst"].isel(time=0, latitude=slice(132,192), longitude=slice(436,496)).values.astype(np.float64))
        ds.close(); ords.append(cur.toordinal()); cur += dt.timedelta(days=1)
    return np.array(out), np.array(ords)

rng = np.random.default_rng(1)
cells = rng.choice(np.argwhere(sea), 3, replace=False)
tests_d = [1, 59, 61, 92, 152, 243, 366]
ok_all = True
for d in tests_d:
    b_dates = ext_ord[bmask & (ext_doy == d)]
    lo = int(min(b_dates)) - 5; hi = int(max(b_dates)) + 5
    arr, ords = load_range(lo, hi)
    P = set()
    for b in b_dates: P.update(range(int(b)-5, int(b)+6))
    m = np.isin(ords, np.fromiter(P, dtype=np.int64))
    pool_bf = arr[m]                      # brute-force pool (nd,60,60)
    for (i, j) in cells:
        vals = pool_bf[:, i, j]
        q_bf = np.percentile(vals[np.isfinite(vals)], 90, method="hazen")
        m_bf = np.mean(vals[np.isfinite(vals)])
        ok1 = np.isclose(q_bf, thr_raw[d-1, i, j], rtol=0, atol=1e-12)
        ok2 = np.isclose(m_bf, clim_raw[d-1, i, j], rtol=0, atol=1e-12)
        if not (ok1 and ok2):
            ok_all = False
            print(f"  MISMATCH d={d} cell=({i},{j}): q {q_bf} vs {thr_raw[d-1,i,j]}, m {m_bf} vs {clim_raw[d-1,i,j]}")
    print(f"d={d}: pool nd={pool_bf.shape[0]} baseline dates={len(b_dates)} checked 3 cells -> {'OK' if ok_all else 'see above'}")
print("ALL brute-force pool checks passed:", ok_all)

# --- day-60 fill check ---
print("day60 == mean(59,61):", bool(np.allclose(thr_raw[59], 0.5*(thr_raw[58]+thr_raw[60]), rtol=0, atol=1e-12) and
                                      np.allclose(clim_raw[59], 0.5*(clim_raw[58]+clim_raw[60]), rtol=0, atol=1e-12)))
# --- smoothing check: naive per-day check on a few (day, cell) combos ---
def naive_smooth_at(a, d):  # 0-based index d of a 366 array
    idx = [(d+o) % 366 for o in range(-15, 16)]
    return np.mean([a[k] for k in idx])
i, j = cells[0]
ok_s = True
for dd in [0, 5, 59, 60, 151, 242, 300, 365]:
    v1 = naive_smooth_at(thr_raw[:, i, j], dd); v2 = thr[dd, i, j]
    v3 = naive_smooth_at(clim_raw[:, i, j], dd); v4 = clim[dd, i, j]
    if not (np.isclose(v1, v2, rtol=0, atol=1e-12) and np.isclose(v3, v4, rtol=0, atol=1e-12)):
        ok_s = False; print(f"  SMOOTH MISMATCH day {dd+1}: {v1} vs {v2}, {v3} vs {v4}")
print("circular smoothing naive checks (incl wrap days 1,366 and day60):", ok_s)
print("thr/clim finite on sea after fill:", bool(np.isfinite(thr[:, sea]).all() and np.isfinite(clim[:, sea]).all()))
print("target finite on sea every day:", bool(np.isfinite(tgt32.astype(np.float64)[:, sea]).all()))
