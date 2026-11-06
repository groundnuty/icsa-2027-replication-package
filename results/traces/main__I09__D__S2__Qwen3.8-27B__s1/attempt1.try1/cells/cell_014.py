import numpy as np
z = np.load('/work/intermediate.npz')
thr, clim = z['thr'], z['clim']
f = np.isfinite(thr[59])
print("finite cells at day60:", int(f.sum()))
print("day60 rule holds on finite cells (thr):", np.allclose(thr[59, f], 0.5*(thr[58, f]+thr[60, f])))
print("day60 rule holds on finite cells (clim):", np.allclose(clim[59, f], 0.5*(clim[58, f]+clim[60, f])))

# also confirm day-60 values are NOT NaN where 59/61 finite
f2 = np.isfinite(thr[58]) & np.isfinite(thr[60])
print("finite 59&61:", int(f2.sum()), "-> day60 finite:", int(np.isfinite(thr[59, f2]).sum()))

# check land vs sea: are all land cells (non-sea) NaN in thr?
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t_all = ds.time.values
u0 = np.searchsorted(t_all, np.datetime64('2022-06-01')); u1 = np.searchsorted(t_all, np.datetime64('2022-08-31'))
S_tgt = ds.analysed_sst.isel(time=slice(u0,u1+1), latitude=slice(66,126), longitude=slice(531,591)).values.astype(np.float64)
ds.close()
sea = np.isfinite(S_tgt).all(axis=0).ravel()
thr_nan = ~np.isfinite(thr).any(axis=0)
print("cells all-NaN thr == non-sea:", bool(np.array_equal(thr_nan, ~sea)))

# MHW gap-join logic unit test (synthetic)
def detect(x, min_len=5, gap=2):
    p = np.concatenate(([0], x, [0]))
    d = np.diff(p.astype(np.int8))
    s = np.flatnonzero(d == 1); e = np.flatnonzero(d == -1) - 1
    keep = (e - s + 1) >= min_len
    s, e = s[keep], e[keep]
    merged = []
    for a, b in zip(s, e):
        if merged and a - merged[-1][1] - 1 <= gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return merged

tests = [
    (list("1111100011111"), [(0,4), (8,12)]),        # two 5-runs, gap 3 -> separate
    (list("111110011111"), [(0,11)]),                # gap 2 -> join
    (list("1111011111"), [(0,9)]),                   # 4-run + 5-run gap 1 -> join
    (list("1111"), []),                              # 4-run -> nothing
    (list("11111"), [(0,4)]),                        # exactly 5
    (list("01111110"), [(1,5)]),                     # 5-run
    (list("1111100111110011111"), [(0,12), (16,20)]),# join then separate
]
ok = True
for x, exp in tests:
    got = detect([int(ch) for ch in x])
    ok &= got == exp
print("gap-join unit tests:", "PASS" if ok else "FAIL")
