import numpy as np, json, datetime as dt
data = np.load('/work/data.npy')
thr_s = np.load('/work/thr_s.npy')
meta = json.load(open('/work/dates.json'))
tg = [dt.date.fromisoformat(s) for s in meta['target']]
tg_data = data[4028:4120]
print('target SST stats: min', np.nanmin(tg_data), 'max', np.nanmax(tg_data), 'mean', np.nanmean(tg_data))
# cell (25,25) series vs threshold
j = 25*60+25
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(d): return cum[d.month-1] + d.day
for k in [0, 30, 60, 91]:
    d = tg[k]
    print(d, 'SST', round(tg_data[k,25,25],3), 'thr', round(thr_s[md_doy(d)-1, 25, 25],3))
# compare distributions: baseline window same cell
bw_data = data[:4028]
print('baseline SST stats: min', np.nanmin(bw_data[:,25,25]), 'max', np.nanmax(bw_data[:,25,25]))
# baseline summer values at this cell
sum_mask = np.array([md_doy(d) in range(152,245) for d in [dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(4028)]])
print('baseline summer mean', np.nanmean(bw_data[sum_mask,25,25]), 'max', np.nanmax(bw_data[sum_mask,25,25]))
print('target summer mean', np.nanmean(tg_data[:,25,25]), 'max', np.nanmax(tg_data[:,25,25]))
