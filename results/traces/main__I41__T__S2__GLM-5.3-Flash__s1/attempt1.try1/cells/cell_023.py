import numpy as np, datetime as dt

B = np.load('work/B.npy').astype(np.float64)   # row0 = 1991-12-27
thr_raw = np.load('work/thr_raw.npy'); clim_raw = np.load('work/clim_raw.npy')
bstart = (dt.date(1991,12,27) - dt.date(1982,1,1)).days  # B[0] date index relative to 1982-01-01

def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n

# centres: baseline years 1992-2002 ONLY
baseline = [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
bdoy = [doy_of(b) for b in baseline]

def pool_dates(d):
    if d == 60: return None
    dates = set()
    for b, do in zip(baseline, bdoy):
        if do == d:
            for off in range(-5, 6):
                dates.add(b + dt.timedelta(days=off))
    return sorted(dates)

# special doy of 2003-01-01 and 1991-12-31 (wrap of leap-style calendar)
print("special doy 2003-01-01:", doy_of(dt.date(2003,1,1)), "(expect 366)")
print("special doy 1991-12-31:", doy_of(dt.date(1991,12,31)), "(expect 366)")
print("special doy 2002-12-31:", doy_of(dt.date(2002,12,31)), "(expect 366)")

ok_thr = True; ok_clim = True
for d in [1, 59, 61, 92, 153, 200, 244, 300, 365, 366]:
    if d == 60: continue
    dates = pool_dates(d)
    rows = np.array([(x - dt.date(1982,1,1)).days - bstart for x in dates])
    assert rows.min() >= 0 and rows.max() < B.shape[0], (d, rows.min(), rows.max())
    pool = B[rows]
    th_ref = np.nanpercentile(pool, 90, axis=0, method='hazen')
    cl_ref = np.nanmean(pool, axis=0)
    mt = np.allclose(th_ref, thr_raw[d-1], rtol=0, atol=1e-9)
    mc = np.allclose(cl_ref, clim_raw[d-1], rtol=0, atol=1e-9)
    ok_thr &= mt; ok_clim &= mc
    print(f"doy {d:3d}: n={len(dates)} range {dates[0]}..{dates[-1]} | thr match {mt} | clim match {mc}")
print("independent pool/threshold/climatology recheck:", "ALL OK" if ok_thr and ok_clim else "FAIL")
