import numpy as np, datetime as dt

z = np.load('/tmp/region_cube.npz', allow_pickle=True)
dates_str = z['dates']; cube32 = z['cube']
BLK = 4028
tc = np.load('/tmp/thr_clim.npz')
thr_raw = tc['thr_raw']; thr = tc['thr']; sea = tc['sea']
cube = cube32[:, :, :60].astype(np.float64)
base = cube[:BLK].reshape(BLK, -1)[:, sea.reshape(-1)]
dates = [dt.datetime.strptime(str(s), '%Y%m%d').date() for s in dates_str]
CUM = [0,31,59,90,120,151,181,212,243,273,304,334]
doy_map = lambda d: CUM[d.month-1]+d.day+(1 if d.month>2 else 0)
doy_arr = np.array([doy_map(d) for d in dates])
anchor_idx = np.arange(5, 5+4018)
sea_idx = np.argwhere(sea)

# brute-force verify thr_raw/clim_raw for a few cells and doys
rng = np.random.default_rng(0)
for trial in range(4):
    ci = int(rng.integers(0, len(sea_idx))); d = int(rng.choice([1, 45, 153, 200, 244, 300, 365, 366]))
    r, c = sea_idx[ci]
    js = anchor_idx[doy_arr[anchor_idx] == d]
    vals = np.concatenate([base[max(0,j-5):min(BLK,j+6), ci] for j in js])
    q = np.quantile(vals, 0.9, method='hazen')
    ok1 = np.isclose(q, thr_raw[d-1, ci]); ok2 = np.isclose(np.mean(vals), tc['clim_raw'][d-1, ci])
    print(f"cell({r},{c}) d={d}: pool n={len(vals)}, thr bf={q:.6f} vs {thr_raw[d-1,ci]:.6f} ok={ok1}; clim ok={ok2}")

# MATLAB quantile default (type 5, hazen) reference check on small vectors
v = np.array([1., 2., 3., 4., 5., 6., 7., 8., 9., 10.])
print("hazen q90 of 1..10:", np.quantile(v, 0.9, method='hazen'), "(MATLAB quantile(v,.90)=9.55)")
v2 = np.array([1., 2., 3., 4.])
print("hazen q50 of 1..4:", np.quantile(v2, 0.5, method='hazen'), "(MATLAB=2.5)")

# hazen formula check: position = p*(n+... ) -> h = p*n + 0.5
def hazen(x, p):
    x = np.sort(np.asarray(x, float)); n = len(x); h = p*n + 0.5
    lo = int(np.floor(h)); frac = h - lo
    return x[lo-1] + frac*(x[min(lo, n)-1+1-1+ (1 if False else 1)-1+1]*0 + (x[min(lo,n-1)] - x[lo-1]))
print("manual hazen q90 1..10:", hazen(v, 0.9))

# daily pattern of hot / mhw cells
mhw = np.load('/tmp/mhw_result.npz')['mhw']; hot = np.load('/tmp/mhw_result.npz')['hot']
CUMd = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
print("\nday        hot   mhw")
for i in range(0, 92, 4):
    print(CUMd[i], f"{hot[i].sum():5d} {mhw[i].sum():5d}")
print(CUMd[91], f"{hot[91].sum():5d} {mhw[91].sum():5d}")
