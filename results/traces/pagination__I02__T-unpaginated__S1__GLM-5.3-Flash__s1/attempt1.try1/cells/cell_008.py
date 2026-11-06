import numpy as np, datetime as dt, time, warnings

t_start = time.time()
z = np.load('mhw_cache.npz', allow_pickle=False)
base_data = z['base_data']; tgt_data = z['tgt_data']

def doy366(d):
    cum_norm = [0,31,59,90,120,151,181,212,243,273,304,334]  # non-leap cumulative
    if d.month == 2 and d.day == 29:
        return 60
    v = cum_norm[d.month-1] + d.day
    if d.month >= 3:
        v += 1
    return v

# verify the spec anchors
anchors = {(2001,1,1):1,(2001,2,28):59,(2000,2,29):60,(2001,3,1):61,(2000,3,1):61,
           (2001,12,31):366,(2000,12,31):366,(1992,12,31):366,(2004,6,1):153,(2004,8,31):244}
for (y,m,dd), exp in anchors.items():
    got = doy366(dt.date(y,m,dd))
    assert got == exp, (y,m,dd,got,exp)
print("doy mapping anchors OK")

EXT_START = dt.date(1991,12,27)
B0, B1 = dt.date(1992,1,1), dt.date(2002,12,31)
ext_days = [EXT_START + dt.timedelta(days=k) for k in range(base_data.shape[0])]
ext_doy  = np.array([doy366(d) for d in ext_days])
is_base  = np.array([B0 <= d <= B1 for d in ext_days])
bi_idx   = np.where(is_base)[0]

pool_idx = [[] for _ in range(367)]
for bi in bi_idx:
    d = ext_doy[bi]
    if d == 60:
        continue
    pool_idx[d].extend(range(bi-5, bi+6))
sizes = [len(p) for p in pool_idx[1:]]
print("pool sizes (d=1..366): min", min(sizes), "max", max(sizes),
      "| d=59:", sizes[58], "d=60:", sizes[59], "d=61:", sizes[60], "d=366:", sizes[365])

NY, NX = base_data.shape[1], base_data.shape[2]
thr = np.full((366, NY, NX), np.nan)
clm = np.full((366, NY, NX), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60: continue
        vals = base_data[pool_idx[d]].astype(np.float64)
        thr[d-1] = np.nanpercentile(vals, 90, axis=0, method='hazen')
        clm[d-1] = np.nanmean(vals, axis=0)
thr[59] = 0.5*(thr[58] + thr[60])
clm[59] = 0.5*(clm[58] + clm[60])

def smooth31(a):
    out = np.zeros_like(a)
    for k in range(-15, 16):
        out += np.roll(a, k, axis=0)
    return out / 31.0
thr_s = smooth31(thr); clm_s = smooth31(clm)
print(f"clim/thr done {time.time()-t_start:.1f}s; NaN cells in thr_s: {int(np.isnan(thr_s[0]).sum())} of {NY*NX}")

np.savez('clim_thr.npz', thr=thr_s, clm=clm_s)
print("sample smoothed thr/clim doy 214 (Aug 1), cell(30,30):", thr_s[213,30,30], clm_s[213,30,30])
