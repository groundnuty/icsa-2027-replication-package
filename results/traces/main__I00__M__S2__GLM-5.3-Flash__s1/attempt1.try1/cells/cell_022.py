import numpy as np, pickle, datetime as dtm

sst = np.load("/tmp/mhw_work/sst.npy").astype("float64")
thresh_raw = np.load("/tmp/mhw_work/thresh_raw.npy")
clim_raw = np.load("/tmp/mhw_work/clim_raw.npy")
meta = pickle.load(open("/tmp/mhw_work/meta.pkl", "rb"))
ordered = meta["ordered"]
pos = {s: i for i, s in enumerate(ordered)}

i, j = 28, 59
for d, (m, day) in [(170, (6,18)), (244, (8,31)), (153, (6,1)), (200, (7,18))]:
    pool = []
    for y in range(1992, 2003):
        c = dtm.date(y, m, day)
        for k in range(-5, 6):
            s = (c + dtm.timedelta(days=k)).strftime("%Y-%m-%d")
            pool.append(sst[pos[s], i, j])
    pool = np.array(pool)
    thr_bf = np.nanquantile(pool, 0.9, method="hazen")
    clim_bf = np.nanmean(pool)
    print(f"doy {d} ({m:02d}-{day:02d}): thresh match {thr_bf == thresh_raw[d-1,i,j]} "
          f"({thr_bf:.10f} vs {thresh_raw[d-1,i,j]:.10f}); "
          f"clim match {clim_bf == clim_raw[d-1,i,j]} ({clim_bf:.10f} vs {clim_raw[d-1,i,j]:.10f})")
