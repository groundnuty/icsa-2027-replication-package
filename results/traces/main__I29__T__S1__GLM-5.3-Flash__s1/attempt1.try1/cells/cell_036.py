import numpy as np, datetime
hot = np.load('hot.npy')
start = datetime.date(2015,6,1)
dates = [start + datetime.timedelta(days=k) for k in range(92)]
per_day = hot.sum(axis=(1,2))
nz = np.where(per_day>0)[0]
print('days with >=1 hot cell:', len(nz))
for i in nz:
    print(dates[i], int(per_day[i]))
