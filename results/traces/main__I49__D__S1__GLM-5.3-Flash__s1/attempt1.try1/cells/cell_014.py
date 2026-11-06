import numpy as np, datetime as dt, warnings

cube = np.load('/work/cube.npy')
dates = [dt.date.fromisoformat(l.strip()) for l in open('/work/dates.txt') if l.strip()]
thresh_s = np.load('/work/thresh_s.npy'); clim_s = np.load('/work/clim_s.npy')

def doy_md(d): return dt.date(2000, d.month, d.day).timetuple().tm_yday

# rebuild raw (unsmoothed) thresh/clim for spot check
B0, B1 = dt.date(1991,12,27), dt.date(2003,1,5)
sel_b = np.array([B0 <= d <= B1 for d in dates])
cube_base = cube[sel_b]; dates_base = [d for d in dates if B0<=d<=B1]
ord_base = np.array([d.toordinal() for d in dates_base])
bl = [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
doy_bl = np.array([doy_md(d) for d in bl]); ord_bl = np.array([d.toordinal() for d in bl])

i, j = 30, 30   # spot-check cell
dtest = 180
Bs = ord_bl[doy_bl == dtest]
mask = np.zeros(len(ord_base), bool)
for B in Bs: mask |= (np.abs(ord_base - B) <= 5)
pool = cube_base[mask][:, i, j]
pool = pool[np.isfinite(pool)]
raw_q = np.quantile(pool, 0.9, method='hazen'); raw_m = pool.mean()
# smooth directly by loop
def direct_smooth(arr366, d):
    idxs = [(d-1+k) % 366 for k in range(-15,16)]
    return np.mean([arr366[k] for k in idxs])
# reconstruct raw arrays for this cell only
raw_thresh_cell = np.full(366, np.nan); raw_clim_cell = np.full(366, np.nan)
for d in range(1,367):
    if d == 60: continue
    Bs = ord_bl[doy_bl == d]
    m2 = np.zeros(len(ord_base), bool)
    for B in Bs: m2 |= (np.abs(ord_base - B) <= 5)
    p = cube_base[m2][:, i, j]; p = p[np.isfinite(p)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw_thresh_cell[d-1] = np.quantile(p, 0.9, method='hazen')
        raw_clim_cell[d-1] = np.mean(p)
raw_thresh_cell[59] = 0.5*(raw_thresh_cell[58]+raw_thresh_cell[60])
raw_clim_cell[59] = 0.5*(raw_clim_cell[58]+raw_clim_cell[60])
print("doy", dtest, "cell(30,30): direct q90 =", raw_q, "vs in-loop =", raw_thresh_cell[dtest-1])
print("doy", dtest, "cell(30,30): direct mean =", raw_m, "vs in-loop =", raw_clim_cell[dtest-1])
print("smoothed thresh doy180 cell(30,30): loop =", direct_smooth(raw_thresh_cell, 180), "vs vectorized =", thresh_s[179,i,j])
print("smoothed clim   doy180 cell(30,30): loop =", direct_smooth(raw_clim_cell, 180), "vs vectorized =", clim_s[179,i,j])
# check wrap-around: doy 1 and doy 366
for dd in [1, 366, 60]:
    print(f"doy {dd}: smoothed thresh loop =", direct_smooth(raw_thresh_cell, dd), "vec =", thresh_s[dd-1,i,j],
          "| clim loop =", direct_smooth(raw_clim_cell, dd), "vec =", clim_s[dd-1,i,j])
# full-grid consistency of direct smoothing vs saved (sample 40 random cells/doys)
rng = np.random.default_rng(0)
maxdiff = 0.0
for _ in range(40):
    ci, cj = rng.integers(0,60,2)
    dd = int(rng.integers(1,367))
    # need raw arrays for this cell: recompute quickly using cached pools? do full loop
    rtc = np.full(366, np.nan)
    for d in range(1,367):
        if d==60: continue
        Bs = ord_bl[doy_bl==d]; m2 = np.zeros(len(ord_base), bool)
        for B in Bs: m2 |= (np.abs(ord_base-B)<=5)
        p = cube_base[m2][:, ci, cj]; p = p[np.isfinite(p)]
        if p.size: rtc[d-1] = np.quantile(p, 0.9, method='hazen')
    rtc[59] = 0.5*(rtc[58]+rtc[60])
    if np.isfinite(rtc).all():
        maxdiff = max(maxdiff, abs(direct_smooth(rtc, dd) - thresh_s[dd-1, ci, cj]))
print("max |direct-loop smoothing - vectorized| over 40 random cell/doy samples:", maxdiff)
