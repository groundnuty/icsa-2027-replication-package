import numpy as np, pickle, time

base = np.load('/tmp/base.npy')          # (4028, 60, 60)
with open('/tmp/pools.pkl', 'rb') as f:
    pools = pickle.load(f)

NC = 60 * 60
thr = np.full((366, NC), np.nan)
clim = np.full((366, NC), np.nan)

t0 = time.time()
for d in list(range(1, 60)) + list(range(61, 367)):
    idx = pools[d]                      # 121 date indices into base
    pool = base[idx]                    # (121, 60, 60)
    thr[d - 1] = np.nanquantile(pool, 0.9, axis=0, method='hazen').reshape(-1)
    clim[d - 1] = np.nanmean(pool, axis=0).reshape(-1)
print(f"loop done in {time.time()-t0:.1f}s")

# day 60 = mean of days 59 and 61 (arrays indexed 0-based: 58, 59, 60)
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

# 31-day centred moving mean, wrapping over 366 days
off = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
thr_s = thr[off].mean(axis=1)   # (366, NC)
clim_s = clim[off].mean(axis=1)
print("smoothed shapes:", thr_s.shape, clim_s.shape)

# sanity: no NaN in smoothed arrays for any cell? (land cells may be NaN)
nan_cells = np.where(np.isnan(thr_s).any(axis=0))[0]
print("cells with any NaN threshold:", len(nan_cells))
finite_cells = 3600 - len(nan_cells)
print("finite-threshold cells:", finite_cells)

np.save('/tmp/thr_s.npy', thr_s)
np.save('/tmp/clim_s.npy', clim_s)

# print a sample: smoothed threshold for a central cell over June 1 - Aug 31 (doy 153..244)
c = 1798  # arbitrary central cell
doy_t = np.arange(153, 245)
print("cell", c, "June/Aug thr sample:", np.round(thr_s[doy_t-1, c][:5], 3), "...", np.round(thr_s[doy_t-1, c][-5:], 3))
print("cell", c, "clim sample:", np.round(clim_s[doy_t-1, c][:5], 3))
