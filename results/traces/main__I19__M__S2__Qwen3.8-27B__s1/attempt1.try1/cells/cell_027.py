script = '''
import numpy as np
import xarray as xr
from datetime import date, timedelta

PATH = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
Z = np.load('/work/interim.npz', allow_pickle=True)
M = np.load('/work/mhw.npz', allow_pickle=True)
thr = Z['thr']; clim = Z['clim']
tgt = Z['tgt']
tgt_dates = np.asarray(Z['tgt_dates'], dtype=str)
mem = M['mem']; sea = M['sea']; active = M['active']
ncells = 3600

ds = xr.open_dataset(PATH, engine="h5netcdf")
lat_all = ds.latitude.values.astype(np.float64); lon_all = ds.longitude.values.astype(np.float64)
tol = 1e-6
li0 = np.where((lat_all >= 57.13-tol) & (lat_all <= 58.33+tol))[0]
lo0 = np.where((lon_all >= 22.79-tol) & (lon_all <= 23.99+tol))[0]

cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_of_d(d):  # (month, day) fixed table
    mm = 1
    for m in range(1, 13):
        if d <= cum[m]:
            return m, d - cum[m-1]
    raise ValueError
def val_at(datestr, li, lo):
    i = int(np.searchsorted(ds.time.values, np.datetime64(datestr)))
    assert str(ds.time[i].astype('datetime64[D]')) == datestr[:10]
    return float(ds.analysed_sst[i, li, lo].values)

def pool_manual(d, li, lo):
    m, dd = md_of_d(d)
    out = []
    for Y in range(1992, 2003):
        b = date(Y, m, dd)
        for k in range(-5, 6):
            t = b + timedelta(days=k)
            out.append(val_at(f"{t.year:04d}-{t.month:02d}-{t.day:02d}", li, lo))
    return np.array(out)

def hazen(x, q=0.9):
    x = x[np.isfinite(x)]; n = len(x)
    if n == 0: return np.nan
    x = np.sort(x)
    h1 = min(max(n*q + 0.5, 1.0), float(n))
    lo_i = int(np.floor(h1)); f = h1 - lo_i
    return x[-1] if lo_i >= n else x[lo_i-1] + f*(x[lo_i]-x[lo_i-1])

# (a) independent pool checks: several (doy, cell) combos incl. edge doys
cases = [(1, 0), (1, 3599), (366, 100), (61, 777), (153, 1234), (244, 2999), (59, 555), (300, 1000)]
for d, c in cases:
    r, col = divmod(c, 60)
    li, lo = int(li0[r]), int(lo0[col])
    p = pool_manual(d, li, lo)
    qm, cm = hazen(p), np.nanmean(p)
    ok1 = (np.isnan(qm) and np.isnan(thr[d-1, c])) or np.isclose(qm, thr[d-1, c])
    ok2 = (np.isnan(cm) and np.isnan(clim[d-1, c])) or np.isclose(cm, clim[d-1, c])
    print(f"doy {d} cell {c}: thr ok={ok1} clim ok={ok2} n={int(np.isfinite(p).sum())}")

# (b) day-60 imputation check: saved thr[59] should be 0.5*(pool59 thr, pool61 thr)
for c in [22, 1500, 3599]:
    r, col = divmod(c, 60)
    li, lo = int(li0[r]), int(lo0[col])
    p59, p61 = pool_manual(59, li, lo), pool_manual(61, li, lo)
    t59, t61 = hazen(p59), hazen(p61)
    print(f"day60 check cell {c}: 0.5*(t59,t61)={0.5*(t59+t61)} saved={thr[59,c]} match={np.isclose(0.5*(t59+t61), thr[59,c])}")

ds.close()

# (c) independent MHW reimplementation (explicit day-loop, different structure)
nt = 92
hot = np.zeros((nt, ncells), dtype=bool)
thr_s = M['thr_s']
doy_t = np.array([cum[int(s[5:7])-1] + int(s[8:10]) for s in tgt_dates])
for i in range(nt):
    hot[i] = (tgt[i].reshape(ncells) >= thr_s[doy_t[i]-1]) & sea

def mhw_cell(h):
    # returns list of (s,e) exclusive; brute force
    n = len(h)
    # find maximal hot runs
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]:
                j += 1
            if j - i + 1 >= 5:
                runs.append([i, j+1])
            i = j + 1
        else:
            i += 1
    # merge runs separated by 1 or 2 cold days
    out = []
    for s, e in runs:
        if out and s - out[-1][1] in (1, 2):
            out[-1][1] = e
        else:
            out.append([s, e])
    return out

bad = 0
for c in range(ncells):
    ev = mhw_cell(hot[:, c])
    m = np.zeros(nt, dtype=bool)
    for s, e in ev:
        m[s:e] = True
    if not np.array_equal(m, mem[:, c]):
        bad += 1
        if bad <= 3:
            print("MISMATCH cell", c, "mine:", ev, "pipeline:", np.where(mem[:,c])[0])
print("independent MHW reimplementation mismatches:", bad, "of", ncells)

# (d) event boundaries
print("first/last target:", tgt_dates[0], tgt_dates[-1])
print("active on Jul 23 (idx 52)?", bool(active[52]), " Jul 24?", bool(active[53]), " Aug 18?", bool(active[78]), " Aug 19?", bool(active[79]))
print("n active days:", int(active.sum()))
# count of cells in MHW on event start day
print("cells in MHW on 2014-07-24:", int(mem[53].sum()), " on 2014-08-18:", int(mem[78].sum()))
'''
open('/work/verify.py','w').write(script)
import runpy
runpy.run_path('/work/verify.py', run_name='__main__')
