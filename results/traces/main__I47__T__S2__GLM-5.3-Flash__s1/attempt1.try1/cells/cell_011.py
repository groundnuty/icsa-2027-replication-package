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
print("mask identical to run-1 mask:", np.array_equal(mhw_final, np.load('/tmp/mhw.npy')))

bi, bj = 28, 30
box_i, box_j = i0r+bi, j0r+bj              # box origin in absolute indices
tgt_box = read_with_retry(lambda hf: hf['analysed_sst'][tA:tB+1, box_i:box_i+6, box_j:box_j+6], tag="tgt")
ext_box = read_with_retry(lambda hf: hf['analysed_sst'][eA:eB+1, box_i:box_i+6, box_j:box_j+6], tag="ext")
ext_dates = dates[eA:eB+1]
sea_b = np.isfinite(tgt_box.astype(np.float64)).all(axis=0)
cells = list(zip(*np.nonzero(sea_b)))[:3]
print("box origin", box_i, box_j, "| sea cells in box:", int(sea_b.sum()), "at", round(time.time()-t0,1), "s")

# ---------- independent reference implementation ----------
def doy_la(d):
    yd = d.timetuple().tm_yday
    return yd if (calendar.isleap(d.year) or d.month < 3) else yd + 1

def hazen_py(vals, p=0.9):
    x = sorted(v for v in vals if v == v)
    n = len(x)
    if n == 0: return float('nan')
    h = p*(n-1) + 1.0
    lo = int(np.floor(h)); frac = h - lo
    lo = max(1, min(lo, n)); hi = min(lo+1, n)
    return x[lo-1] if frac == 0 else x[lo-1] + frac*(x[hi-1]-x[lo-1])

abs_cells = [(box_i+a, box_j+b) for a, b in cells]
date_vals = [{ext_dates[k].astype(dt.date): float(ext_box[k, a, b]) for k in range(len(ext_dates))}
             for (a, b) in cells]

base_dates = [dt.date(1992,1,1) + dt.timedelta(days=k)
              for k in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days + 1)]
by_doy = {}
for d in base_dates:
    by_doy.setdefault(doy_la(d), []).append(d)

thr_raw_py = [None]*3; clim_raw_py = [None]*3
for ci in range(3):
    dv = date_vals[ci]
    tr = [None]*366; cr = [None]*366
    for d in range(1, 367):
        if d == 60: continue
        pool = []
        for bd in by_doy[d]:
            for k in range(-5, 6):
                v = dv.get(bd + dt.timedelta(days=k))
                if v is not None: pool.append(v)
        assert len(pool) == 121, (d, len(pool))
        tr[d-1] = hazen_py(pool)
        fin = [v for v in pool if v == v]
        cr[d-1] = sum(fin)/len(fin) if fin else float('nan')
    tr[59] = 0.5*(tr[58] + tr[60]); cr[59] = 0.5*(cr[58] + cr[60])
    thr_raw_py[ci] = tr; clim_raw_py[ci] = cr
print("reference pools built (all ==121 values):", round(time.time()-t0,1), "s")

def smooth_py(raw):
    return [sum(raw[(d+k) % 366] for k in range(-15, 16))/31.0 for d in range(366)]

def mhw_py(hotlist):
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
doy_t_py = [doy_la(d.astype(dt.date)) for d in target_dates]
all_ok = True
for ci, (ai, aj) in enumerate(abs_cells):
    thr_s = smooth_py(thr_raw_py[ci]); clim_s = smooth_py(clim_raw_py[ci])
    br, bc = ai - box_i, aj - box_j                       # box-relative
    hot = []
    for k in range(92):
        sst = float(tgt_box[k, br, bc])
        hot.append(sst == sst and sst >= thr_s[doy_t_py[k]-1])
    mhw_col = mhw_py(hot)
    saved = mhw_final[:, ai - i0r, aj - j0r].astype(bool)  # region-relative
    ok = np.array_equal(np.array(mhw_col), saved)
    all_ok &= ok
    print(f"cell {ai},{aj}: hot={sum(hot)}d, ref-mhw={sum(mhw_col)}d, saved-mhw={int(saved.sum())}d -> MATCH={ok}")
    print(f"   thr doy200={thr_s[199]:.6f} clim doy200={clim_s[199]:.6f} | "
          f"thr doy1={thr_s[0]:.6f} thr doy366={thr_s[365]:.6f}")
print("INDEPENDENT END-TO-END VERIFICATION:", "PASSED" if all_ok else "FAILED")

evs = json.load(open('/tmp/events_final.json'))["events"]
for e in evs:
    a = int((np.datetime64(e["onset"]) - target_dates[0]) / np.timedelta64(1, 'D'))
    b = int((np.datetime64(e["end"]) - target_dates[0]) / np.timedelta64(1, 'D'))
    cnt = mhw_final[a:b+1].reshape(b-a+1, -1).sum(axis=1)
    print(f"event {e['onset']}..{e['end']}: cells/day min {cnt.min()} max {cnt.max()} mean {cnt.mean():.0f}")
print("total", round(time.time()-t0,1), "s")
