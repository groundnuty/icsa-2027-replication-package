import numpy as np, datetime as dt

me = '/work/me/'
thr_s = np.load(me+'thr_s.npy'); clim_s = np.load(me+'clim_s.npy')
b64 = np.load(me+'base.npy').astype(np.float64)
epoch = dt.date(1991,12,27)
seeds = {d: [] for d in range(1,367)}
cur = dt.date(1992,1,1)
while cur <= dt.date(2002,12,31):
    seeds[dt.date(2000,cur.month,cur.day).timetuple().tm_yday].append((cur-epoch).days)
    cur += dt.timedelta(days=1)
Nb = b64.shape[0]
def raw_clim(d):
    if d == 60:
        return None
    m = np.zeros(Nb, bool)
    for s in seeds[d]: m[max(0,s-5):min(Nb,s+6)] = True
    return np.nanmean(b64[m], axis=0)
y, x = 10, 10
raw = np.empty(366)
for d in range(1,367):
    if d == 60: continue
    raw[d-1] = raw_clim(d)[y, x]
raw[59] = 0.5*(raw[58] + raw[60])   # day 60 = mean of days 59,61
# correct checks now (31-element windows)
print("d1  smooth %.6f vs %.6f" % (clim_s[0,y,x], np.concatenate([raw[351:366], raw[0:16]]).mean()))
print("d60 smooth %.6f vs %.6f" % (clim_s[59,y,x], raw[44:75].mean()))
print("d366 smooth %.6f vs %.6f" % (clim_s[365,y,x], raw[350:366].mean()))
print("d2  smooth %.6f vs %.6f" % (clim_s[1,y,x], raw[352:367].mean() if False else np.concatenate([raw[352:366], raw[0:17]]).mean()))
print("d153 smooth %.6f vs %.6f" % (clim_s[152,y,x], raw[137:168].mean()))
