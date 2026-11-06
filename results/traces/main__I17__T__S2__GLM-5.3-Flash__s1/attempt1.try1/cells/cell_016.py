import numpy as np, datetime as dt, fsspec, h5netcdf

me = '/work/me/'
target = np.load(me+'target.npy'); base = np.load(me+'base.npy')
tt = np.load(me+'times_target.npy'); tb = np.load(me+'times_base.npy')
thr_s = np.load(me+'thr_s.npy'); clim_s = np.load(me+'clim_s.npy')
t64 = target.astype(np.float64); b64 = base.astype(np.float64)

# --- 1. brute-force pool check for cell (10,10), doy 200 ---
y, x, d = 10, 10, 200
dates_base = [dt.date(1991,12,27) + dt.timedelta(days=int(k)) for k in range(len(tb))]
seed_dates = [ddt for ddt in dates_base if ddt.year in range(1992,2003) and
              dt.date(2000, ddt.month, ddt.day).timetuple().tm_yday == d]
pool_vals = []
for sd in seed_dates:
    for k, ddt in enumerate(dates_base):
        if abs((ddt - sd).days) <= 5:
            v = b64[k, y, x]
            if np.isfinite(v): pool_vals.append(v)
pool_vals = np.array(pool_vals)
q_bf = np.quantile(pool_vals, 0.9, method='hazen')
m_bf = pool_vals.mean()

# recompute unsmoothed thr/clim for this cell/doy
epoch = dt.date(1991,12,27)
seeds = {dd: [] for dd in range(1,367)}
cur = dt.date(1992,1,1)
while cur <= dt.date(2002,12,31):
    seeds[dt.date(2000,cur.month,cur.day).timetuple().tm_yday].append((cur-epoch).days)
    cur += dt.timedelta(days=1)
Nb = b64.shape[0]
m = np.zeros(Nb, bool)
for s in seeds[d]: m[max(0,s-5):min(Nb,s+6)] = True
vals = b64[m][:, y, x]
q = np.nanquantile(vals, 0.9, method='hazen'); mn = np.nanmean(vals)
print("doy200 cell(10,10): brute n=%d  q=%.6f vs %.6f  mean=%.6f vs %.6f" %
      (len(pool_vals), q_bf, q, m_bf, mn))
# unsmoothed value at day 244 should equal smoothed mean of raw 229..259
raw_q = np.empty(366); raw_q[:] = np.nan
for dd in range(1,367):
    if dd == 60: continue
    mm = np.zeros(Nb, bool)
    for s in seeds[dd]: mm[max(0,s-5):min(Nb,s+6)] = True
    raw_q[dd-1] = np.nanquantile(b64[mm][:, y, x], 0.9, method='hazen')
raw_q[59] = 0.5*(raw_q[58]+raw_q[60])
print("check smooth d244: %.6f vs mean raw 229..259: %.6f" % (thr_s[243,y,x], raw_q[228:259].mean()))
print("check smooth d1  : %.6f vs mean raw 352..366,1..15: %.6f" %
      (thr_s[0,y,x], np.concatenate([raw_q[351:366], raw_q[0:15]]).mean()))

# --- 2. verify subset against remote file for a random target & baseline day ---
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
nc = h5netcdf.File(f,'r'); v = nc['analysed_sst']
traw = np.asarray(nc['time'][:])
tall = np.datetime64('1981-01-01T00:00:00') + traw.astype('timedelta64[s]')
for lbl, tref, sub in [("target 2010-07-15", np.datetime64('2010-07-15'), target),
                       ("base 1997-03-08", np.datetime64('1997-03-08'), base)]:
    j = int(np.where(tall == tref)[0][0])
    remote = np.asarray(v[j, 157:217, 562:622])
    k = int(np.where((tt if lbl.startswith('t') else tb) == tref)[0][0])
    print(lbl, "subset==remote:", np.array_equal(sub[k], remote))

# --- 3. event edges ---
active = np.load(me+'active.npy')
tdates = [str(x.astype('datetime64[D]')) for x in tt]
print("active:", tdates[0], tdates[-1])
print("active days:", [tdates[i] for i in range(92) if active[i]][:3], "...",
      [tdates[i] for i in range(92) if active[i]][-3:])
print("2010-06-28 active?", active[27], " 2010-08-27 active?", active[87])
gaps = [(tdates[i], tdates[i+1]) for i in range(91) if active[i] != active[i+1]]
print("active transitions:", gaps)
