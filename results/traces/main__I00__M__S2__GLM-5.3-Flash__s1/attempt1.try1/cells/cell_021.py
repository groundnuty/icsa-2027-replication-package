import numpy as np, pickle, datetime as dtm, warnings

sst = np.load("/tmp/mhw_work/sst.npy").astype("float64")
in_win = np.load("/tmp/mhw_work/in_win.npy")
thresh_raw = np.load("/tmp/mhw_work/thresh_raw.npy")
clim_raw = np.load("/tmp/mhw_work/clim_raw.npy")
meta = pickle.load(open("/tmp/mhw_work/meta.pkl", "rb"))
ordered = meta["ordered"]
pos = {s: i for i, s in enumerate(ordered)}

i, j = 28, 59
d = 170  # June 19 in leap-style numbering

# brute force pool: baseline dates within +-5 calendar days of June 19, years 1992-2002
pool = []
centers = []
for y in range(1992, 2003):
    centers.append(dtm.date(y, 6, 19))
for c in centers:
    for k in range(-5, 6):
        s = (c + dtm.timedelta(days=k)).strftime("%Y-%m-%d")
        pool.append(sst[pos[s], i, j])
pool = np.array(pool)
print("pool size:", len(pool), "nan:", int(np.isnan(pool).sum()))
thr_bf = np.nanquantile(pool, 0.9, method="hazen")
clim_bf = np.nanmean(pool)
print("brute-force  thresh:", thr_bf, " in-array:", thresh_raw[d-1, i, j])
print("brute-force  clim:  ", clim_bf, " in-array:", clim_raw[d-1, i, j])
print("match:", thr_bf == thresh_raw[d-1, i, j], clim_bf == clim_raw[d-1, i, j])

# also manual hazen implementation check
v = np.sort(pool[~np.isnan(pool)])
n = len(v)
h = n*0.9 + 0.5
lo = int(np.floor(h)); hi = int(np.ceil(h))
gam = h - lo
manual = (1-gam)*v[lo-1] + gam*v[hi-1]
print("manual hazen:", manual, "== numpy hazen:", manual == thr_bf)

# second cell and doy near year boundary (d=2)
d2 = 2
pool2 = []
for y in range(1992, 2003):
    for k in range(-5, 6):
        c = dtm.date(y, 1, 2)
        s = (c + dtm.timedelta(days=k)).strftime("%Y-%m-%d")
        if s in pos:
            pool2.append(sst[pos[s], i, j])
pool2 = np.array(pool2)
print("\ndoy 2 pool size (with spillover):", len(pool2))
print("brute-force thresh:", np.nanquantile(pool2, 0.9, method="hazen"), "in-array:", thresh_raw[d2-1, i, j])
print("brute-force clim:", np.nanmean(pool2), "in-array:", clim_raw[d2-1, i, j])
