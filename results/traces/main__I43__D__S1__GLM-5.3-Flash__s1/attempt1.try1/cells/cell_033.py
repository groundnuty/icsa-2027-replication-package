import numpy as np, pickle, datetime as dt, json
data = np.load('/work/data.npy')
pools = pickle.load(open('/work/pools.pkl','rb'))
bw = [dt.date.fromisoformat(s) for s in json.load(open('/work/dates.json'))['baseline_window']]
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(d): return cum[d.month-1] + d.day
j = 25*60+25
flat = data[:4028].reshape(4028, 3600)

# raw (unsmoothed) threshold doy 213 (index 212) from pool
d = 213
vals = flat[pools[d]][:, j]
thr_raw = np.quantile(vals, 0.9, method='hazen')
print('raw thr doy 213:', round(thr_raw,3), 'pool mean:', round(vals.mean(),3), 'pool size:', len(vals))
# smoothed thr at doy 213
thr_s = np.load('/work/thr_s.npy')
print('smoothed thr doy 213:', round(float(thr_s[212, j]),3))
# What does SST >= RAW threshold give?
thr_t = thr_s[[md_doy(x)-1 for x in [dt.date(2017,6,1)+dt.timedelta(days=i) for i in range(92)]]]
tg_data = data[4028:4120]
# using RAW thresholds instead:
raw_thr = np.empty(366)
for dd in range(1,367):
    if dd == 60: continue
    raw_thr[dd-1] = np.quantile(flat[pools[dd]][:, j], 0.9, method='hazen')
raw_thr[59] = 0.5*(raw_thr[58]+raw_thr[60])
hot_raw = (tg_data[:,25,25] >= raw_thr[[md_doy(x)-1 for x in [dt.date(2017,6,1)+dt.timedelta(days=i) for i in range(92)]]])
print('hot days at cell (25,25) with RAW thr:', int(hot_raw.sum()), 'of 92')
