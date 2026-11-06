import numpy as np, json, datetime as dt
data = np.load('/work/data.npy')
thr_s = np.load('/work/thr_s.npy')  # (366, 3600)
meta = json.load(open('/work/dates.json'))
tg = [dt.date.fromisoformat(s) for s in meta['target']]
tg_data = data[4028:4120]
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(d): return cum[d.month-1] + d.day
j = 25*60+25
for k in [0, 30, 60, 91]:
    d = tg[k]
    print(d, 'SST', round(float(tg_data[k,25,25]),3), 'thr', round(float(thr_s[md_doy(d)-1, j]),3))
bw_data = data[:4028]
print('baseline cell min/max:', round(float(np.nanmin(bw_data[:,25,25])),2), round(float(np.nanmax(bw_data[:,25,25])),2))
sum_mask = np.array([md_doy(dt.date(1991,12,27)+dt.timedelta(days=i)) in range(152,245) for i in range(4028)])
print('baseline summer mean/max at cell:', round(float(np.nanmean(bw_data[sum_mask,25,25])),2), round(float(np.nanmax(bw_data[sum_mask,25,25])),2))
print('target summer mean/max at cell:', round(float(np.nanmean(tg_data[:,25,25])),2), round(float(np.nanmax(tg_data[:,25,25])),2))
