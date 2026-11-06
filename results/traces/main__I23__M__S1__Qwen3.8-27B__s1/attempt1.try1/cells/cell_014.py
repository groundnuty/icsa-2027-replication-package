import numpy as np, json, datetime as dt

OUT="/tmp/mhw"
ext = np.load(f"{OUT}/ext.npy").reshape(4028, 3600)
tgt = np.load(f"{OUT}/tgt.npy").reshape(92, 3600)
thr_s = np.load(f"{OUT}/thr_s.npy")
clim_s = np.load(f"{OUT}/clim_s.npy")
sea = np.load(f"{OUT}/sea.npy")
D_tgt = np.load(f"{OUT}/D_tgt.npy")
dates = json.load(open(f"{OUT}/dates.json"))
ext_dates = [dt.date.fromisoformat(s) for s in dates["ext_dates"]]
tgt_dates = [dt.date.fromisoformat(s) for s in dates["tgt_dates"]]
MS = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doy = lambda d: MS[d.month-1]+d.day
ext_idx = {d:i for i,d in enumerate(ext_dates)}
base_dates = ext_dates[5:5+4018]

def hazen90(x):
    x = np.sort(x)
    n = len(x)
    h = (n+1)*0.9
    j = int(np.floor(h))
    g = h - j
    a = x[j-1] if j-1 >= 0 else x[0]
    b = x[j] if j < n else x[n-1]
    return a + g*(b-a)

def naive_pool_values(c, d):
    vals = []
    for b in base_dates:
        if doy(b) != d: continue
        for k in range(-5, 6):
            t = b + dt.timedelta(days=k)
            if t in ext_idx:
                v = ext[ext_idx[t], c]
                if np.isfinite(v):
                    vals.append(v)
    return np.array(vals)

def naive_thr(c, d):
    v = naive_pool_values(c, d)
    return hazen90(v) if len(v) else np.nan

def naive_clim(c, d):
    v = naive_pool_values(c, d)
    return v.mean() if len(v) else np.nan

def naive_smooth(arr, d0):  # arr: 366-array (0-based doy index), d0 leap doy 1..366
    vals = [arr[(d0-1+dd-15) % 366] for dd in range(31)]
    return np.mean(vals)

# rebuild unsmoothed arrays? I only saved smoothed. Recompute unsmoothed for the same cells quickly using saved smoothed? 
# Instead: recompute unsmoothed for a couple of doys using saved arrays is impossible; recompute via naive and compare to a fresh vectorized run for those doys.
sea_idx = np.flatnonzero(sea)
for c in sea_idx[:3]:
    for d in (153, 168, 183):
        print("cell",c,"doy",d,
              "naive_thr", round(naive_thr(c,d),9),
              "naive_clim", round(naive_clim(c,d),9),
              "nvals", len(naive_pool_values(c,d)))
