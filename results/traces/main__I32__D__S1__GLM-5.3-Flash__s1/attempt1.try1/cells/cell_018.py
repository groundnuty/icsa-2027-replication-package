import numpy as np, h5py, json, time as _time
from datetime import date, timedelta
from scipy.signal import fftconvolve

B = np.load('/work/B.npy')          # (4028, 60, 60) baseline window 1991-12-27..2003-01-05
T = np.load('/work/T.npy')          # (92, 60, 60)  target 2005-06-01..2005-08-31
meta = json.load(open('/work/meta.json'))
b0 = date.fromisoformat(meta['b0']); b1 = date.fromisoformat(meta['b1'])
t0 = date.fromisoformat(meta['t0']); t1 = date.fromisoformat(meta['t1'])
nb = (b1-b0).days+1; nt = (t1-t0).days+1
bdates = [b0+timedelta(days=i) for i in range(nb)]
tdates = [t0+timedelta(days=i) for i in range(nt)]

# cross-check consolidated file vs daily shard file for 1992-06-01
i_chk = (date(1992,6,1)-b0).days
fd = h5py.File('/work/daily/sst_19920601.nc','r')
la0,la1,lo0,lo1 = meta['la0'],meta['la1'],meta['lo0'],meta['lo1']
vd = fd['analysed_sst'][0, la0:la1, lo0:lo1].astype(np.float64)
both_finite = np.isfinite(vd) & np.isfinite(B[i_chk])
print("daily-vs-consolidated equal (finite):", np.array_equal(vd[both_finite], B[i_chk][both_finite]))
print("finite pattern identical:", np.array_equal(np.isfinite(vd), np.isfinite(B[i_chk])))
fd.close()

CUM366 = [0,31,60,91,121,152,182,213,244,274,305,335]
doy_of = lambda d: CUM366[d.month-1] + d.day
bdoy = np.array([doy_of(d) for d in bdates])
tdoy = np.array([doy_of(d) for d in tdates])
print("baseline window doys present:", np.unique(bdoy))
print("target doys:", tdoy[0], "...", tdoy[-1])

# sea cells: finite on every target day
sea = np.isfinite(T).all(axis=0)
print("sea cells:", int(sea.sum()), "of", sea.size)

# ---- pools, threshold (hazen p90), climatology (mean) ----
t1m = _time.time()
thr = np.full((366, 60, 60), np.nan)
clm = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    offs = np.arange(d-5, d+6)
    offs = np.where(offs < 1, offs+366, offs)
    offs = np.where(offs > 366, offs-366, offs)
    sel = np.isin(bdoy, offs)
    pool = B[sel]                      # (n,60,60) includes NaN on land
    thr[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clm[d-1] = np.nanmean(pool, axis=0)
print("pool loop time", _time.time()-t1m)
# day 60 from neighbours
thr[59] = (thr[58] + thr[60]) / 2.0
clm[59] = (clm[58] + clm[60]) / 2.0
print("thr finite everywhere:", np.isfinite(thr).all(), " clim finite:", np.isfinite(clm).all())
np.save('/work/thr_raw.npy', thr); np.save('/work/clm_raw.npy', clm)

# sample: cell with sea=True
sc = np.argwhere(sea)
r,c = sc[len(sc)//2]
print("sample cell", r, c, "thr d153,d244:", thr[152,r,c], thr[243,r,c], "clim:", clm[152,r,c], clm[243,r,c])
