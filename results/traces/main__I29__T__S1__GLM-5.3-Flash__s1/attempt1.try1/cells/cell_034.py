import numpy as np, datetime
tgt = np.load('target.npy').astype(np.float64)
thresh = np.load('thresh.npy'); thresh_raw = np.load('thresh_raw.npy'); clim = np.load('clim.npy')
start = datetime.date(2015,6,1)
dates = [start + datetime.timedelta(days=k) for k in range(92)]

# pick a sea cell, e.g. (5,5) and (30,30)
for cell in [(5,5),(30,30),(15,45)]:
    i,j = cell
    s = tgt[:,i,j]; t = thresh[[151+min(k,243-151) for k in range(92)],i,j]
    print('cell', cell, 'SST Jun1..Aug31 min/max/mean:', np.nanmin(s).round(3), np.nanmax(s).round(3), np.nanmean(s).round(3))
    print('  threshold min/max over period:', t.min().round(3), t.max().round(3))
    print('  first 10 SST:', s[:10].round(2))
    print('  first 10 thresh:', t[:10].round(2))
    hot_n = (s >= t).sum()
    print('  hot days at this cell:', hot_n)
