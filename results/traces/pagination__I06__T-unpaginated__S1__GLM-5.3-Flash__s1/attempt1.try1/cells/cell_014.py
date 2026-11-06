import numpy as np, datetime as dt, pickle, time, warnings

base_sst = np.load('/tmp/base_sst.npy')
with open('/tmp/meta.pkl','rb') as f:
    meta = pickle.load(f)
base_dates = [dt.date.fromisoformat(s) for s in meta['base_dates']]

def doy366(d):
    if d.month == 2 and d.day == 29:
        return 60
    if d.month <= 2:
        return (d - dt.date(d.year,1,1)).days + 1
    return 61 + (d - dt.date(d.year,3,1)).days

B0, B1 = dt.date(1992,1,1), dt.date(2002,12,31)
pool_idx = {}
for xi, X in enumerate(base_dates):
    for off in range(-5, 6):
        B = X + dt.timedelta(days=off)
        if B0 <= B <= B1:
            d = doy366(B)
            if d != 60:
                pool_idx.setdefault(d, []).append(xi)

bs64 = base_sst.astype(np.float64)
thr_raw = np.full((367, 60, 60), np.nan)
clim_raw = np.full((367, 60, 60), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        block = bs64[pool_idx[d]]
        thr_raw[d] = np.nanpercentile(block, 90, axis=0, method='hazen')
        clim_raw[d] = np.nanmean(block, axis=0)
thr_raw[60] = 0.5*(thr_raw[59] + thr_raw[61])
clim_raw[60] = 0.5*(clim_raw[59] + clim_raw[61])
t366 = thr_raw[1:]; c366 = clim_raw[1:]

# ---- brute force in float128 (near-exact reference) ----
def brute128(a):
    a128 = a.astype(np.longdouble)
    out = np.empty_like(a128)
    for j in range(366):
        idxs = [(j+k) % 366 for k in range(-15,16)]
        out[j] = a128[idxs].mean(axis=0)
    return out
ref_t = brute128(t366); ref_c = brute128(c366)

# method A: cumsum padded
def movA(a):
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(ap, axis=0)
    cp = np.concatenate([np.zeros((1,)+a.shape[1:]), c], axis=0)
    return (cp[31:] - cp[:-31]) / 31.0
# method B: roll-sum
def movB(a):
    return sum(np.roll(a, -k, axis=0) for k in range(-15,16)) / 31.0
# method C: direct index-mean per day
def movC(a):
    return np.stack([a[[(j+k) % 366 for k in range(-15,16)]].mean(axis=0) for j in range(366)])

for name, fn in [("A cumsum", movA), ("B rollsum", movB), ("C indexmean", movC)]:
    et = np.abs(fn(t366).astype(np.longdouble) - ref_t).max()
    ec = np.abs(fn(c366).astype(np.longdouble) - ref_c).max()
    print(f"{name}: max |err| vs float128 ref  thr={float(et):.3e}  clim={float(ec):.3e}")

thr = movA(t366); clim = movA(c366)
targ_sst = np.load('/tmp/targ_sst.npy')
sea = np.isfinite(targ_sst.astype(np.float64)).all(axis=0)
print("sea cells:", sea.sum())
print("thr finite on sea:", np.isfinite(thr[:, sea]).all(), " clim finite on sea:", np.isfinite(clim[:, sea]).all())
print("thr sample (cell 30,30): doy152-156:", np.round(thr[151:156, 30, 30], 4))
print("clim sample (cell 30,30): doy152-156:", np.round(clim[151:156, 30, 30], 4))
print("thr range:", thr.min(), thr.max(), " clim range:", clim.min(), clim.max())

np.save('/tmp/thr.npy', thr)      # entry j = day j+1
np.save('/tmp/clim.npy', clim)
with open('/tmp/pools.pkl','wb') as f:
    pickle.dump({str(k): v for k, v in pool_idx.items()}, f)
print("saved thr, clim, pools")
