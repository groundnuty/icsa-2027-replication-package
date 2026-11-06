
import numpy as np, datetime as dt
hot = np.load('/tmp/mhw/hot.npy')
maskA = np.load('/tmp/mhw/maskA.npy')
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(92)]
active = maskA.any(axis=1)
print("check mapping: tdates[49..66]")
for k in range(49, 67):
    print(k, tdates[k], "hot:", int(hot[k].sum()), "maskA:", int(maskA[k].sum()), "active:", bool(active[k]))
print("event2 from earlier: 2008-07-24 -> 2008-08-03")
# find indices of those dates
print("Jul24 idx:", tdates.index(dt.date(2008,7,24)), " Aug3 idx:", tdates.index(dt.date(2008,8,3)))
