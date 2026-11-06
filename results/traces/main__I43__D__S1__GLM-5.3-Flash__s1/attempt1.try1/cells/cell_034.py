import numpy as np, pickle, datetime as dt, json
data = np.load('/work/data.npy')
thr_s = np.load('/work/thr_s.npy').reshape(366,60,60)
clim_s = np.load('/work/clim_s.npy').reshape(366,60,60)
meta = json.load(open('/work/dates.json'))
bw = [dt.date.fromisoformat(s) for s in meta['baseline_window']]
tg = [dt.date.fromisoformat(s) for s in meta['target']]
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(d): return cum[d.month-1] + d.day

# in-sample exceedance over baseline window
bw_data = data[:4028]
bw_doy = np.array([md_doy(d) for d in bw])
thr_bw = thr_s[bw_doy-1]
exc = (bw_data >= thr_bw)
valid = np.isfinite(bw_data)
print('in-sample exceedance rate (sea cells, baseline):', round(float(exc[valid].mean()),4))
# per year
years = np.array([d.year for d in bw])
for y in range(1992,2003):
    m = years == y
    print(y, round(float(exc[m][valid[m]].mean()),4))
# 2017 vs climatology
tg_data = data[4028:4120]
tg_doy = np.array([md_doy(d) for d in tg])
anom = tg_data - clim_s[tg_doy-1]
print('2017 anomaly: mean', round(float(np.nanmean(anom)),2), 'min', round(float(np.nanmin(anom)),2), 'max', round(float(np.nanmax(anom)),2))
print('days with positive regional-mean anomaly:', int((np.nanmean(anom,axis=(1,2))>0).sum()), 'of 92')
