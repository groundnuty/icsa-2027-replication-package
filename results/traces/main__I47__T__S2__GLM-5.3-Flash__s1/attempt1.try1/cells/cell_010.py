import numpy as np, json, os, time, datetime as dt, calendar
import fsspec, h5py

t0 = time.time()
PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
fs = fsspec.filesystem('onedata')
def read_with_retry(fn, tries=4, tag=""):
    last = None
    for k in range(tries):
        hf = None
        try:
            hf = h5py.File(fs.open(PATH, 'rb'), 'r')
            out = fn(hf)
            try: hf.close()
            except Exception: pass
            return out
        except Exception as e:
            last = e; time.sleep(2 + 2*k)
    raise last

lat, lon, dates = read_with_retry(lambda hf: (hf['latitude'][:], hf['longitude'][:],
    (np.datetime64('1981-01-01') + hf['time'][:].astype('timedelta64[s]')).astype('datetime64[D]')), tag="meta")
i0r, i1r = 545, 605; j0r, j1r = 721, 781
def idx_of(s): return int((np.datetime64(s) - dates[0]) / np.timedelta64(1, 'D'))
tA, tB = idx_of('2019-06-01'), idx_of('2019-08-31')
eA, eB = idx_of('1991-12-27'), idx_of('2003-01-05')

mhw_final = np.load('/tmp/mhw_final.npy')
mhw_run1  = np.load('/tmp/mhw.npy')
print("mask identical to run-1 mask:", np.array_equal(mhw_final, mhw_run1))

# pick a small box with >=3 sea cells
box = None
for (bi, bj) in [(28, 30), (10, 40), (45, 15)]:
    tgt = read_with_retry(lambda hf: hf['analysed_sst'][tA:tB+1, i0r+bi:i0r+bi+6, j0r+bj:j0r+bj+6], tag="box")
    sea_b = np.isfinite(tgt.astype(np.float64)).all(axis=0)
    if sea_b.sum() >= 3:
        box = (bi, bj, tgt, sea_b); break
assert box is not None
bi, bj, tgt_box, sea_b = box
cells = list(zip(*np.nonzero(sea_b)))[:3]
abs_cells = [(i0r+bi+a, j0r+bj+b) for a, b in cells]
print("verification cells (abs lat/lon idx):", abs_cells)

ext_box = read_with_retry(lambda hf: hf['analysed_sst'][eA:eB+1, i0r+bi:i0r+bi+6, j0r+bj:j0r+bj+6], tag="extbox")
ext_dates = dates[eA:eB+1]
print("boxes read at", round(time.time()-t0, 1), "s")

# ---------- independent reference implementation (pure python) ----------
def doy_leap_aligned(d):  # independent formula via tm_yday
    yd = d.timetuple().tm_yday
    return yd if (calendar.isleap(d.year) or d.month < 3) else yd + 1

def hazen_py(vals, p=0.9):  # MATLAB default piecewise, 1-based virtual index
    x = sorted(v for v in vals if v == v)
    n = len(x)
    if n == 0: return float('nan')
    h = p*(n-1) + 1.0
    lo = int(np.floor(h)); frac = h - lo
    hi = min(lo+1, n)
    lo = max(1, min(lo, n))
    return x[lo-1] if frac == 0 else x[lo-1] + frac*(x[hi-1]-x[lo-1])

# date -> value dicts per verification cell
date_vals = []
for (ai, aj) in [(a-i0r, b-j0r) for a, b in abs_cells]:
    date_vals.append({ext_dates[k].astype(dt.date): float(ext_box[k, a, b]) for k in range(len(ext_dates))})

base_dates = [dt.date(1992, 1, 1) + dt.timedelta(days=k) for k in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days + 1)]
by_doy = {}
for d in base_dates:
    by_doy.setdefault(doy_leap_aligned(d), []).append(d)

thr_raw_py = [[None]*366 for _ in range(3)]
clim_raw_py = [[None]*366 for _ in range(3)]
for ci in range(3):
    dv = date_vals[ci]
    for d in range(1, 367):
        if d == 60: continue
        pool = []
        for bd in by_doy[d]:
            for k in range(-5, 6):
                dd = bd + dt.timedelta(days=k)
                v = dv.get(dd)
                if v is not None: pool.append(v)
        assert len(pool) == 121, (d, len(pool))
        thr_raw_py[ci][d-1] = hazen_py(pool)
        fin = [v for v in pool if v == v]
        clim_raw_py[ci][d-1] = sum(fin)/len(fin) if fin else float('nan')
    thr_raw_py[ci][59] = 0.5*(thr_raw_py[ci][58] + thr_raw_py[ci][60])
    clim_raw_py[ci][59] = 0.5*(clim_raw_py[ci][58] + clim_raw_py[ci][60])

def smooth_py(raw):  # circular 31-day centred mean, pure python
    return [sum(raw[(d+k) % 366] for k in range(-15, 16))/31.0 for d in range(366)]

def mhw_py(hotlist):  # runs >=5, join gaps <=2
    runs, i, T = [], 0, len(hotlist)
    while i < T:
        if hotlist[i]:
            j = i
            while j+1 < T and hotlist[j+1]: j += 1
            runs.append([i, j]); i = j+1
        else: i += 1
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
        else: merged.append([a, b])
    out = [False]*T
    for a, b in merged:
        for k in range(a, b+1): out[k] = True
    return out

target_dates = dates[tA:tB+1]
tdate_py = [d.astype(dt.date) for d in target_dates]
doy_t_py = [doy_leap_aligned(d) for d in tdate_py]

all_ok = True
for ci, (ai, aj) in enumerate(abs_cells):
    thr_s = smooth_py(thr_raw_py[ci])
    clim_s = smooth_py(clim_raw_py[ci])
    dv = date_vals[ci]
    hot_py, mhw_py_col = [], None
    hot = []
    for k in range(92):
        sst = float(read_cache[tgt_box[k, ai-i0r, aj-j0r]]) if False else float(tgt_box[k, ai-i0r, aj-j0r])
        hot.append(sst == sst and sst >= thr_s[doy_t_py[k]-1])
    mhw_py_col = mhw_py(hot)
    saved = mhw_final[:, ai-i0r+0, aj-j0r].astype(bool)  # box offset == abs-i0r since box starts at region corner? NO
    saved = mhw_final[:, ai - i0r, aj - j0r].astype(bool)
    ok = np.array_equal(np.array(mhw_py_col), saved)
    all_ok &= ok
    print(f"cell {ai},{aj}: independent hot days={sum(hot)}, mhw days={sum(mhw_py_col)}, "
          f"saved mhw days={int(saved.sum())}, MATCH={ok}")
    print(f"   sample thr/clim doy200: {thr_s[199]:.6f} / {clim_s[199]:.6f} K, "
          f"doy1: {thr_s[0]:.6f} K, doy366: {thr_s[365]:.6f} K")
print("INDEPENDENT END-TO-END VERIFICATION:", "PASSED" if all_ok else "FAILED")

# per-event stats from saved mask
evs = json.load(open('/tmp/events_final.json'))["events"]
for e in evs:
    a = int((np.datetime64(e["onset"]) - target_dates[0]) / np.timedelta64(1, 'D'))
    b = int((np.datetime64(e["end"]) - target_dates[0]) / np.timedelta64(1, 'D'))
    cnt = mhw_final[a:b+1].reshape(b-a+1, -1).sum(axis=1)
    print(f"event {e['onset']}..{e['end']}: cells/day min {cnt.min()}, max {cnt.max()}, mean {cnt.mean():.0f}")
