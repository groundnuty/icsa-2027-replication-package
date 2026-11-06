import numpy as np, xarray as xr, datetime, time, warnings

t0 = time.time()
ext = np.load('/work/ext.npy')
ncells = ext.shape[1]
ext_dates = []
d = datetime.date(1991,12,27)
while d <= datetime.date(2003,1,5):
    ext_dates.append(d); d += datetime.timedelta(days=1)
d2i = {dt: i for i, dt in enumerate(ext_dates)}
lat_idx = np.load('/work/lat_idx.npy'); lon_idx = np.load('/work/lon_idx.npy')
Nlat = len(lat_idx)
def flat(r,c): return r*Nlat + c

canon = {}
for dnum in range(1, 367):
    if dnum <= 59: dt = datetime.date(2001,1,1) + datetime.timedelta(days=dnum-1)
    elif dnum == 60: dt = datetime.date(2004,2,29)
    else: dt = datetime.date(2001,3,1) + datetime.timedelta(days=dnum-61)
    canon[dnum] = (dt.month, dt.day)

thr_raw = np.full((366, ncells), np.nan); clim_raw = np.full((366, ncells), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    for dnum in range(1, 367):
        if dnum == 60: continue
        m, dd = canon[dnum]
        idxs = []
        for y in range(1992, 2003):
            i0 = d2i[datetime.date(y, m, dd)]
            idxs.extend(range(i0-5, i0+6))
        pool = ext[np.asarray(idxs)]
        thr_raw[dnum-1] = np.nanquantile(pool, 0.9, axis=0, method="hazen")
        clim_raw[dnum-1] = np.nanmean(pool, axis=0)
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])

def smooth31(arr):
    out = np.zeros_like(arr)
    for k in range(-15, 16):
        out += np.roll(arr, k, axis=0)
    return out / 31.0
thr_chk = smooth31(thr_raw); clim_chk = smooth31(clim_raw)

thr = np.load('/work/thr.npy'); clim = np.load('/work/clim.npy')
print("smoothed arrays identical to rerun:", np.array_equal(thr, thr_chk), np.array_equal(clim, clim_chk))

# raw verification vs independent (doy 166, cell (10,10))
print("RAW thr[165] indep 284.5139953613281 vs saved", thr_raw[165, flat(10,10)], "equal:", np.isclose(284.5139953613281, thr_raw[165, flat(10,10)]))
print("RAW clim[165] indep 279.94544818972753 vs saved", clim_raw[165, flat(10,10)], "equal:", np.isclose(279.94544818972753, clim_raw[165, flat(10,10)]))
print("RAW thr[60] indep 273.2599792480469 vs saved", thr_raw[60, flat(30,40)], "equal:", np.isclose(273.2599792480469, thr_raw[60, flat(30,40)]))

# smoothing check at (165, flat(10,10))
w = np.array([thr_raw[(165 + k) % 366, flat(10,10)] for k in range(-15,16)])
print("smoothed[165] vs mean of raw[150..170]:", thr[165, flat(10,10)], w.mean(), np.isclose(thr[165, flat(10,10)], w.mean()))
# wrap-around check at doy=1 (index 0): should average indices 351..365,0..15
w0 = np.array([thr_raw[(0 + k) % 366, flat(10,10)] for k in range(-15,16)])
print("wrap smoothed[0]:", thr[0, flat(10,10)], w0.mean(), np.isclose(thr[0, flat(10,10)], w0.mean()))
# doy 60 fill check
print("raw[59] == mean(raw[58],raw[60]):", np.allclose(thr_raw[59], 0.5*(thr_raw[58]+thr_raw[60])))

np.save('/work/thr_raw.npy', thr_raw); np.save('/work/clim_raw.npy', clim_raw)
print("done", time.time()-t0)
