import numpy as np, datetime
tgt = np.load('target.npy').astype(np.float64)
clim = np.load('clim.npy'); thresh = np.load('thresh.npy')
hot = np.load('hot.npy')
def doy_of(d):
    y = d.timetuple().tm_yday
    leap = (d.year%4==0 and d.year%100!=0) or (d.year%400==0)
    return y if leap or y < 60 else y+1
start = datetime.date(2015,6,1)
dates = [start + datetime.timedelta(days=k) for k in range(92)]
tdoy = np.array([doy_of(d) for d in dates])
anom = tgt - clim[tdoy-1]
print('regional mean anomaly (SST - clim): mean %.2f K, min %.2f, max %.2f' % (
    np.nanmean(anom), np.nanmin(anom), np.nanmax(anom)))
per_day_anom = np.nanmean(anom, axis=(1,2))
print('warmest days by regional mean anomaly:')
for i in np.argsort(per_day_anom)[-5:][::-1]:
    print('  ', dates[i], round(per_day_anom[i],2))
print('coolest:')
for i in np.argsort(per_day_anom)[:3]:
    print('  ', dates[i], round(per_day_anom[i],2))
# hot cell-days
print('total hot cell-days:', int(hot.sum()), '| hot days per day max:', int(hot.sum(axis=(1,2)).max()))
