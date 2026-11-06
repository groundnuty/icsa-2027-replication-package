import numpy as np, datetime as dt

B = np.load('work/B.npy').astype(np.float64)
T = np.load('work/T.npy').astype(np.float64)
thr_raw = np.load('work/thr_raw.npy'); clim_raw = np.load('work/clim_raw.npy')
thr_s = np.load('work/thr_s.npy'); clim_s = np.load('work/clim_s.npy')
bstart = (dt.date(1991,12,27) - dt.date(1982,1,1)).days
sea = np.isfinite(T).all(axis=0)

def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n

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

ok = True
for d in [1, 59, 61, 92, 153, 200, 244, 300, 365, 366]:
    dates = pool_dates(d)
    rows = np.array([(x - dt.date(1982,1,1)).days - bstart for x in dates])
    pool = B[rows]
    th_ref = np.nanpercentile(pool, 90, axis=0, method='hazen')
    cl_ref = np.nanmean(pool, axis=0)
    # compare on sea cells only
    mt = np.allclose(th_ref[sea], thr_raw[d-1][sea], rtol=0, atol=1e-9)
    mc = np.allclose(cl_ref[sea], clim_raw[d-1][sea], rtol=0, atol=1e-9)
    # also check land cells are NaN in both
    lt = np.array_equal(np.isnan(th_ref), np.isnan(thr_raw[d-1]))
    lc = np.array_equal(np.isnan(cl_ref), np.isnan(clim_raw[d-1]))
    ok &= mt and mc and lt and lc
    print(f"doy {d:3d}: thr {mt} clim {mc} nan-pattern {lt and lc} (n={len(dates)})")
print("independent recheck of raw threshold/climatology:", "ALL OK" if ok else "FAIL")

# also verify smoothing independently with brute force on sea cells for a few doys
ok_s = True
for d in [1, 60, 153, 244, 366]:
    idxs = [(d-1+k) % 366 for k in range(-15, 16)]
    bf_thr = thr_raw[idxs][:, sea.any(axis=0) if False else slice(None)].mean(axis=0)  # placeholder
    # brute force properly:
    acc_t = np.zeros_like(thr_raw[0]); acc_c = np.zeros_like(clim_raw[0])
    for k in idxs:
        acc_t += thr_raw[k]; acc_c += clim_raw[k]
    bf_t = acc_t/31.0; bf_c = acc_c/31.0
    mt = np.allclose(bf_t[sea], thr_s[d-1][sea], rtol=0, atol=1e-9)
    mc = np.allclose(bf_c[sea], clim_s[d-1][sea], rtol=0, atol=1e-9)
    ok_s &= mt and mc
    print(f"smoothing doy {d:3d}: thr {mt} clim {mc}")
print("independent smoothing recheck:", "ALL OK" if ok_s else "FAIL")
