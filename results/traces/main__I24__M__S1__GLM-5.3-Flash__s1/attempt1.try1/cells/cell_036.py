import numpy as np, datetime as dt
inmhw=np.load('/tmp/inmhw.npy')
dates=[dt.date.fromordinal(int(o)) for o in np.load('/tmp/dates_ord.npy')]
ti=4540
active=inmhw.any(axis=(1,2))
for k in range(92):
    if active[k]: print(str(dates[ti+k]), 'cells in mhw:',int(inmhw[k].sum()))
print('cells ever in mhw:',int(inmhw.any(axis=0).sum()))
# daily count of cells in mhw around event
import collections
