import numpy as np, datetime as dt, warnings, time, os
print("cwd:", os.getcwd())
cube = np.load('/work/cube.npy')
dates = [dt.date.fromisoformat(l.strip()) for l in open('/work/dates.txt') if l.strip()]
print("cube:", cube.shape, "dates:", dates[0], dates[-1])

def doy_md(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

# baseline slice incl. +-5 day extensions
B0, B1 = dt.date(1991,12,27), dt.date(2003,1,5)
sel_b = np.array([B0 <= d <= B1 for d in dates])
cube_base = cube[sel_b]
dates_base = [d for d in dates if B0 <= d <= B1]
ord_base = np.array([d.toordinal() for d in dates_base])
print("baseline slice:", len(dates_base), dates_base[0], dates_base[-1])

# baseline dates proper
bl = [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
doy_bl = np.array([doy_md(d) for d in bl])
ord_bl = np.array([d.toordinal() for d in bl])
print("baseline dates:", len(bl), bl[0], bl[-1])

# cell finiteness diagnostics
fin_base = np.isfinite(cube_base).sum(axis=0)
fin_tgt  = np.isfinite(cube).sum(axis=0)  # placeholder, refined below
sel_t = np.array([dt.date(2019,6,1) <= d <= dt.date(2019,8,31) for d in dates])
cube_t = cube[sel_t]
dates_t = [d for d in dates if dt.date(2019,6,1) <= d <= dt.date(2019,8,31)]
fin_tgt = np.isfinite(cube_t).sum(axis=0)
T = len(dates_t)
vals, cnts = np.unique(fin_tgt, return_counts=True)
print("target finite-day histogram (value: ncells):", dict(zip(vals.tolist(), cnts.tolist())))
vals2, cnts2 = np.unique(fin_base, return_counts=True)
print("baseline finite-day histogram:", dict(zip(vals2.tolist(), cnts2.tolist())))

# pools
t0 = time.time()
thresh = np.full((366,)+cube.shape[1:], np.nan)
clim   = np.full((366,)+cube.shape[1:], np.nan)
pool_sizes = []
for d in range(1, 367):
    if d == 60:
        continue
    Bs = ord_bl[doy_bl == d]
    mask = np.zeros(len(ord_base), dtype=bool)
    for B in Bs:
        mask |= (np.abs(ord_base - B) <= 5)
    pool = cube_base[mask]
    pool_sizes.append(pool.shape[0])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        thresh[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim[d-1]   = np.nanmean(pool, axis=0)
pool_sizes = np.array(pool_sizes)
print(f"pools done in {time.time()-t0:.1f}s | pool size min/max:", pool_sizes.min(), pool_sizes.max())

# day 60 fill
thresh[59] = 0.5*(thresh[58] + thresh[60])
clim[59]   = 0.5*(clim[58] + clim[60])

# circular 31-day centred moving mean
def circ31(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    cs = np.concatenate([np.zeros((1,)+a.shape[1:]), np.cumsum(ext, axis=0)], axis=0)
    return (cs[31:] - cs[:-31]) / 31.0
thresh_s = circ31(thresh)
clim_s   = circ31(clim)
print("smoothed shapes:", thresh_s.shape, clim_s.shape)

np.save('/work/thresh_s.npy', thresh_s)
np.save('/work/clim_s.npy', clim_s)
np.save('/work/cube_t.npy', cube_t)
with open('/work/dates_t.txt','w') as f:
    for d in dates_t: f.write(d.isoformat()+"\n")

# diagnostics: NaN pattern of smoothed thresh over target doys
doy_t = np.array([doy_md(d) for d in dates_t])
th_t = thresh_s[doy_t-1]
sea = fin_tgt == T
print("sea cells (finite all target days):", sea.sum(), "of", sea.size)
print("smoothed thresh NaN fraction over target doys, sea cells:", np.isnan(th_t[:, sea]).mean())
print("smoothed thresh NaN fraction over target doys, land cells:", np.isnan(th_t[:, ~sea]).mean())
# sample: cell (30,30) threshold & clim around mid-summer
i=j=30
print("cell(30,30) thresh doy 153..160:", np.round(thresh_s[152:160, i, j], 3))
print("cell(30,30) clim   doy 153..160:", np.round(clim_s[152:160, i, j], 3))
print("all smoothed-finite cells == sea cells?", np.array_equal(np.isfinite(thresh_s).all(axis=0), sea))
