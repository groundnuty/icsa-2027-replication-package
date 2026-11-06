
import numpy as np, datetime, json, time

t0 = time.time()
X = np.concatenate([np.load(f'work/part_{t}.npy') for t in ('b1','b2','b3')], axis=0)  # (4028,60,60)
Xt = np.load('work/part_t1.npy')  # (92,60,60)
print("X:", X.shape, Xt.shape)

# --- dates ---
d0 = datetime.date(1991,12,27)
dates = [d0 + datetime.timedelta(days=i) for i in range(X.shape[0])]
assert dates[0].isoformat() == '1991-12-27' and dates[-1].isoformat() == '2003-01-05', (dates[0], dates[-1])
tdates = [datetime.date(2007,6,1) + datetime.timedelta(days=i) for i in range(Xt.shape[0])]
assert tdates[0].isoformat() == '2007-06-01' and tdates[-1].isoformat() == '2007-08-31'
print("dates ok:", len(dates), len(tdates))

# --- fixed (leap-year calendar) day-of-year mapping ---
DIMS = [31,29,31,30,31,30,31,31,30,31,30,31]
prefix = [0]
for x in DIMS: prefix.append(prefix[-1]+x)
def doy(dt):  # 1..366, Jan 1=1, Feb 28=59, Feb 29=60, Mar 1=61, Dec 31=366
    return prefix[dt.month-1] + dt.day
assert doy(datetime.date(2000,2,28)) == 59
assert doy(datetime.date(2000,2,29)) == 60
assert doy(datetime.date(2000,3,1)) == 61
assert doy(datetime.date(2000,12,31)) == 366
assert doy(datetime.date(2007,6,1)) == 153
assert doy(datetime.date(2007,8,31)) == 244

# --- baseline dates and pools ---
B0, B1 = datetime.date(1992,1,1), datetime.date(2002,12,31)
bmap = {}
d = B0
while d <= B1:
    bmap[d] = doy(d)
    d += datetime.timedelta(days=1)
print("baseline dates:", len(bmap))

pool = {d: [] for d in range(1, 367)}
for i, t in enumerate(dates):
    for k in range(-5, 6):
        b = t + datetime.timedelta(days=k)
        if b in bmap:
            pool[bmap[b]].append(i)

sizes = {}
for d in range(1, 367):
    if d == 60: continue
    sizes[d] = len(pool[d])
import collections
cnt = collections.Counter(sizes.values())
print("pool size distribution:", dict(cnt))
assert all(len(pool[d]) == 121 for d in range(1,367) if d != 60)
print("pool building ok", time.time()-t0)

# --- threshold (90th pct, hazen) and climatology (mean), per day of year ---
thr = np.full((366, X.shape[1]*X.shape[2]), np.nan)
cli = np.full((366, X.shape[1]*X.shape[2]), np.nan)
ncell = X.shape[1]*X.shape[2]
for d in range(1, 367):
    if d == 60: continue
    blk = X[np.array(pool[d])].reshape(len(pool[d]), ncell)
    thr[d-1] = np.nanquantile(blk, 0.9, axis=0, method='hazen')
    cli[d-1] = np.nanmean(blk, axis=0)

# day 60 = mean of days 59 and 61 (before smoothing)
thr[59] = (thr[58] + thr[60]) / 2.0
cli[59] = (cli[58] + cli[60]) / 2.0
print("raw threshold/clim computed", time.time()-t0)

# --- 31-day centred moving mean, wrapping (day d averages d-15..d+15 mod 366) ---
def smooth31(raw):
    out = np.zeros_like(raw)
    for k in range(-15, 16):
        out += np.roll(raw, -k, axis=0)
    out /= 31.0
    return out
thr_s = smooth31(thr)
cli_s = smooth31(cli)
print("smoothing done", time.time()-t0)

np.save('work/thr_s.npy', thr_s)
np.save('work/cli_s.npy', cli_s)

# --- sea cells: finite on every target day ---
sea = np.all(np.isfinite(Xt), axis=0)  # (60,60)
print("sea cells:", int(sea.sum()), "of", ncell)

# NaN check for target DOY window (153..244) at sea cells
tday_doy = np.array([doy(td) for td in tdates])
print("target DOY range:", tday_doy.min(), tday_doy.max())
nan_target = np.isnan(thr_s[tday_doy-1][:, sea.ravel()])
print("NaN smoothed threshold among sea cells in target window:", int(nan_target.sum()))

np.save('work/sea.npy', sea)
np.save('work/tday_doy.npy', tday_doy)
print("done", time.time()-t0)
