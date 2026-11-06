script = r'''
import numpy as np, pickle, time, warnings

t0 = time.time()
sst = np.load("/tmp/mhw_work/sst.npy").astype("float64")   # (4840, 60, 60)
in_win = np.load("/tmp/mhw_work/in_win.npy")               # (367, 4840)
targ_pos = np.load("/tmp/mhw_work/targ_pos.npy")

nlat, nlon = sst.shape[1], sst.shape[2]
thresh_raw = np.full((366, nlat, nlon), np.nan)
clim_raw = np.full((366, nlat, nlon), np.nan)

pool_counts_sea = []
finite_all = np.isfinite(sst[targ_pos]).all(axis=0)

warnings.filterwarnings("ignore")
for d in range(1, 367):
    if d == 60:
        continue
    m = in_win[d]                       # (4840,) bool
    vals = sst[m]                       # (121, 60, 60)
    v2 = vals.reshape(vals.shape[0], -1)  # (121, 3600)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clim_raw[d-1] = np.nanmean(v2, axis=0)
        thresh_raw[d-1] = np.nanquantile(v2, 0.9, axis=0, method="hazen")
    # pool NaN count check for sea cells
    cnt = np.isfinite(v2).sum(axis=0)
    pool_counts_sea.append(cnt[finite_all])

pool_counts_sea = np.array(pool_counts_sea)  # (365, n_sea)
print("pool sizes over sea cells: min", pool_counts_sea.min(), "max", pool_counts_sea.max())
print("any sea cell missing pool values:", bool((pool_counts_sea != 121).any()))

# day 60 <- mean of days 59 and 61 (raw)
thresh_raw[59] = 0.5*(thresh_raw[58] + thresh_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print("day 60 filled. NaN cells in thresh_raw (land):", int(np.isnan(thresh_raw).any(axis=0).sum()))
print("thresh_raw sea range:", np.nanmin(thresh_raw[:, finite_all]), np.nanmax(thresh_raw[:, finite_all]))
print("clim_raw sea range:", np.nanmin(clim_raw[:, finite_all]), np.nanmax(clim_raw[:, finite_all]))

# sample values for one central-ish sea cell (index of max finiteness, pick lat/lon mid)
sc = np.argwhere(finite_all)
mid = sc[len(sc)//2]
print("sample sea cell (i,j):", mid)
i, j = mid
print("  thresh_raw doy 150,170,200,240:", [round(float(thresh_raw[d-1,i,j]),4) for d in (150,170,200,240)])
print("  clim_raw   doy 150,170,200,240:", [round(float(clim_raw[d-1,i,j]),4) for d in (150,170,200,240)])

np.save("/tmp/mhw_work/thresh_raw.npy", thresh_raw)
np.save("/tmp/mhw_work/clim_raw.npy", clim_raw)
print("saved. elapsed", time.time()-t0)
'''
open("/tmp/mhw_work/compute_stats.py", "w").write(script)
exec(open("/tmp/mhw_work/compute_stats.py").read())
